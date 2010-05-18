
#Metric for consistency in USASpending versus CFDA reported obligations

from settings import *
from cfda.models import *
from metrics.models import AgencyConsistency, ProgramConsistency
from django.db.models import Avg, Sum
import csv
import numpy as np
import math


def main():
    
    assistance_type = 1 #default to grants and direct assistance
    if len(sys.argv) > 1:
        assistance_type = sys.argv[1]
    
    nonreporting = 0
    underreporting = 0
    overreporting = 0
    
    agency_writer = csv.writer(open('csv/agency_stats_%s.csv' % assistance_type, 'w'))
    program_writer = csv.writer(open('csv/program_stats_%s.csv' % assistance_type, 'w'))

    agency_writer.writerow(('Agency Name', 'Fiscal Year', 'CFDA Obligations', 'USASpending Obligations', 'Avg underreporting %', 'underreporting % std', 'Avg overreporting %', 'overreporting % std', 'Non-reporting Programs', 'Non-reporting obligations', '% of obligations NOT reported', 'Total programs'))
    program_writer.writerow(('Program Number', 'Program Name', 'Fiscal Year', 'Agency', 'CFDA Obligations', 'USASpending Obligations', 'Delta', 'Percent under/over reported'))

    fin_programs = Program.objects.filter(types_of_assistance__financial=True ).distinct()
    fin_obligations = ProgramObligation.objects.filter(program__in=fin_programs, type=assistance_type)

    for fy in FISCAL_YEARS:
        nr_programs = fin_obligations.filter(usaspending_obligation=None, fiscal_year=fy, type=assistance_type)
        nonreporting = len(nr_programs)

        under_programs = fin_obligations.filter(fiscal_year=fy, weighted_delta__lt=0).exclude(program__in=nr_programs)
        under_floats = [float(v) for v in under_programs.values_list('weighted_delta', flat=True)]
        underreporting = len(under_programs)

        over_programs = fin_obligations.filter(fiscal_year=fy, weighted_delta__gt=0)
        over_floats = [float(v) for v in over_programs.values_list('weighted_delta', flat=True)]
        overreporting = len(over_programs)

        exact = fin_obligations.filter(fiscal_year=fy, weighted_delta=0)
        
        #calc some basic stats
        under_stats = calc_stats(under_floats)
        over_stats = calc_stats(over_floats)

        #The student loan program is totally screwing up finding less obscene outliers. Here's a hack:
        #calculate new stats with outliers > 5 standard deviations left out
        new_under = under_programs.filter(weighted_delta__gte=str(-5*under_stats['std']))
        new_over = over_programs.filter(weighted_delta__lte=str((5*over_stats['std'])))
        under_stats = calc_stats([float(v) for v in new_under.values_list('weighted_delta', flat=True)])
        over_stats = calc_stats([float(v) for v in new_over.values_list('weighted_delta', flat=True)])

        under_outliers = [ under_programs.filter(weighted_delta__lte=str(-under_stats['std']), weighted_delta__gte=str(-2*under_stats['std'])), 
                        under_programs.filter(weighted_delta__lte=str(-2*under_stats['std']), weighted_delta__gte=str(-3*under_stats['std'])), 
                        under_programs.filter(weighted_delta__lte=str(-3*under_stats['std']))]

        over_outliers = [over_programs.filter(weighted_delta__gte=str(over_stats['std']), 
                        weighted_delta__lte=str(2*over_stats['std'])), 
                        over_programs.filter(weighted_delta__gte=str(2*over_stats['std']), weighted_delta__lte=str(3*over_stats['std'])), 
                        over_programs.filter(weighted_delta__gte=str(3*over_stats['std']))]
        
        print fy
        print "\nNumber of non reporting programs: %s\nNumber of underreporting programs: %s\nNumber of overreporting programs: %s\nExact:%s" % (nonreporting, underreporting, overreporting, len(exact))
        
        print "STD of underreported values:%s\nSTD of overreported values:%s\n" % (under_stats['std'], over_stats['std'])
        print "weighted avg of underreporting programs:%s\nweighted average of overreporting programs:%s\n" % (under_stats['avg'], over_stats['avg'])
        
        #convert to float from weirdo numpy float format
        under_std = float(under_stats['std'])
        under_avg = float(under_stats['avg'])
        over_std = float(over_stats['std'])
        over_avg = float(over_stats['std'])
        
        good = 0
        bad = 0
        ok = 0

        for agency in Agency.objects.all():
            score_agency(agency, fin_obligations, fy, agency_writer, assistance_type)

        for prog in fin_programs:
            obs = ProgramObligation.objects.filter(program=prog, fiscal_year=fy, type=assistance_type)
            for p in obs:
		
                #add program consistency metric
                try:
                    pcm = ProgramConsistency.objects.get(fiscal_year=fy, program=prog, type=assistance_type)
                except ProgramConsistency.DoesNotExist:    
                    pcm = ProgramConsistency(fiscal_year=fy, program=prog, type=assistance_type, agency=prog.agency)

                try:
                    if p.weighted_delta:
                        prog_wd = float(str(p.weighted_delta))
                        if prog_wd < 0:
                            pcm.under_reported_dollars = p.delta
                            pcm.under_reported_pct = p.weighted_delta
                            if prog_wd < (under_avg - under_std): 
                                bad += float(p.obligation)
                                p.grade = 'u'
                            elif prog_wd < under_avg: 
                                ok += float(p.obligation)
                                p.grade = 'p'
                            elif prog_wd > under_avg: 
                                good += float(p.obligation)
                                p.grade = 'p'
                        elif prog_wd > 0:
                            pcm.over_reported_dollars = p.delta
                            pcm.over_reported_pct = p.weighted_delta
                            if prog_wd > (over_avg + over_std): 
                                bad += float(p.obligation)
                                p.grade = 'o'
                            elif prog_wd > over_avg: 
                                ok += float(p.obligation)
                                p.grade = 'p'
                            elif prog_wd < over_avg: 
                                good += float(p.obligation)
                                p.grade = 'p'
                    else:
                        if p.usaspending_obligation is None and p.obligation is not None and p.obligation != 0:
                            bad += float(p.obligation)
                            p.grade = 'n'
                            pcm.non_reported_dollars = p.delta
                            pcm.non_reported_pct = p.weighted_delta

                        elif p.weighted_delta == 0:
                            good += float(p.obligation)
                            p.grade = 'p'
                           
                        else:  
                            print "weighted delta is none: %s\t%s\t%s\t%s" % (p.program.program_number, p.program.program_title, p.obligation, p.usaspending_obligation)

                    p.save()
                    pcm.save() 
                    program_writer.writerow((p.program.program_number, p.program.program_title.replace(u'\u2013', "").replace(u'\xa0', ''), fy, p.program.agency.name, p.obligation, p.usaspending_obligation, p.delta, p.weighted_delta)) 
                except UnicodeEncodeError, e:
                    print e
                    print "%s - %s" % (p.program.program_number, p.program.program_title)

        #temp hack to show a summary of what programs would be excluded
        #program_writer.writerow(('',fy, "good:", good, "ok: ", ok, "bad: ", bad))

def score_agency(agency, fin_obligations, fiscal_year, writer, type):
    
    obs = fin_obligations.filter(program__agency=agency,fiscal_year=fiscal_year)
    under = obs.filter(delta__lt=0)
    over = obs.filter(delta__gt=0)
    exact = obs.filter(delta=0)
    avg_under_pct = under.aggregate(Avg('weighted_delta'))['weighted_delta__avg'] or 0 
    avg_over_pct = over.aggregate(Avg('weighted_delta'))['weighted_delta__avg'] or 0
    unreported = obs.filter(usaspending_obligation=None, obligation__gt=0)

    summary = obs.aggregate(Sum('obligation'), Sum('usaspending_obligation'))
    under_summary = under.aggregate(Sum('delta'))
    over_summary = over.aggregate(Sum('delta'))
    
    weighted_delta_list = [float(v) for v in over.values_list('weighted_delta', flat=True)]
    over_sd = np.std(weighted_delta_list)
    under_sd = np.std(weighted_delta_list)
    over_var = np.var(weighted_delta_list)
    under_var = np.var(weighted_delta_list)
    nr_sum = unreported.aggregate(Sum('obligation'))['obligation__sum'] or 0
    or_sum = over.aggregate(Sum('obligation'))['obligation__sum'] or 0
    ur_sum = under.aggregate(Sum('obligation'))['obligation__sum'] or 0
    try:
        nr_pct = nr_sum / summary['obligation__sum']
    except Exception, e:
        nr_pct = 0

    if obs:
        ac_collection = AgencyConsistency.objects.filter(agency=agency, fiscal_year=fiscal_year, type=type)
        if len(ac_collection) == 0:
            ac = AgencyConsistency(fiscal_year=fiscal_year, agency=agency, type=type)
        else:
            ac = ac_collection[0]

        ac.total_cfda_obligations = summary['obligation__sum'] or 0
        ac.total_usa_obligations = summary['usaspending_obligation__sum'] or 0
        ac.total_programs = str(len(obs))
        ac.non_reported_dollars = str(nr_sum)
        ac.under_reported_dollars = str(ur_sum)
        ac.over_reported_dollars = str(or_sum) 
        try:
            ac.under_reported_pct = str(ur_sum / ac.total_cfda_obligations)
            ac.over_reported_pct = str(or_sum / ac.total_cfda_obligations)
            ac.non_reported_pct = str(nr_sum / ac.total_cfda_obligations)
        except Exception:
            #divide by 0 error
            ac.under_reported_pct = str(0)
            ac.over_reported_pct = str(0)
            ac.non_reported_pct = str(0)
        ac.avg_under_pct = str(avg_under_pct)
        ac.avg_over_pct = str(avg_over_pct)
        ac.std_under_pct = str(under_sd)
        ac.std_over_pct = str(over_sd)
        ac.var_under_pct = str(under_var)
        ac.var_over_pct = str(over_var)
        
        ac.save() #save to be able to add to many to many
        for nr_ob in unreported:
            if nr_ob.program not in ac.non_reporting_programs.all():
                ac.non_reporting_programs.add(nr_ob.program)
        
        ac.save()

        writer.writerow((agency.name, fiscal_year, summary['obligation__sum'], summary['usaspending_obligation__sum'], avg_under_pct, under_sd, avg_over_pct, over_sd, len(unreported), nr_sum, nr_pct, len(obs)))

def calc_stats(float_array):
    stats = {}
    stats['avg'] = np.average(float_array)
    stats['std'] = np.std(float_array)
    stats['var'] = np.var(float_array)

    return stats

if __name__ == '__main__':
    main()
    
         

