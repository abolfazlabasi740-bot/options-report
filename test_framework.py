from reporting.report_engine import list_reports
from reporting.reports.lmp_report import LMPReport
from reporting.reports.base_share_ranking import BaseShareRankingReport

print('گزارش‌های ثبت‌شده:', list_reports())
print()

lmp = LMPReport()
sample_results = [
    {'ردیف': 1, 'نماد': 'ضخزر۱۲۴۵', 'نوع': 'کال', 'قیمت پایه': 3250, 'قیمت اعمال': 4000,
     'سقف قیمت': 4200, 'پرمیوم': '12%', 'سود خام': 550, 'سربه‌سر': 3850, 'امتیاز': 8.5, 'وضعیت': 'مجاز',
     'symbol': 'ضخزر۱۲۴۵', 'strike': 4000, 'premium': '12%', 'break_even': 3850, 'score': 8.5, 'status': 'مجاز'},
]
sample_unmatched = [{'symbol': 'ضوع۱', 'reason': 'نگاشت ناموفق'}]
sample_no_ceiling = [{'symbol': 'خگستر', 'base': 'خگستر'}]

j = lmp.to_json(sample_results, sample_unmatched, sample_no_ceiling, {'fixed_growth': None})
print('LMP JSON keys:', list(j.keys()))
print('  run_id:', j['run_id'])
print('  validation_pass:', j['validation_pass'])
print('  score_summary:', j['score_summary'])
print('  no_ceiling count:', len(j['no_ceiling']))
print('  ranking_top:', j['ranking_top'])
print()

bsr = BaseShareRankingReport()
sample_shares = [
    {'symbol': 'خگستر', 'industry': 'دارو', 'price': 3250, 'pe': 12.5, 'roe': 28,
     'liquidity': 'بالا', 'avg_volume': '5M', 'change': '+2%', 'score': 9.2, 'status': 'مجاز'},
    {'symbol': 'فملی', 'industry': 'فلز', 'price': 8900, 'pe': 8.1, 'roe': 22,
     'liquidity': 'بالا', 'avg_volume': '8M', 'change': '-1%', 'score': 7.5, 'status': 'مجاز'},
]
j2 = bsr.to_json(bsr.build_rows(sample_shares)[0])
print('BSR JSON keys:', list(j2.keys()))
print('  run_id:', j2['run_id'])
print('  validation_pass:', j2['validation_pass'])
print('  opportunities:', j2['opportunities'])
print('  ranking_top:', j2['ranking_top'])
print()
print('✅ هر دو گزارش با فریم‌ورک مشترک اجرا شدند')
