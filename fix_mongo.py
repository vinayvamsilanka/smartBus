import re

with open('backend/app/admin/routes.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replacements
code = code.replace('.objects().count()', '.query.count()')
code = code.replace('City.objects().order_by("-id")', 'City.query.order_by(City.id.desc()).all()')
code = code.replace('Route.objects().order_by("-id")', 'Route.query.order_by(Route.id.desc()).all()')
code = code.replace('Bus.objects().order_by("-id")', 'Bus.query.order_by(Bus.id.desc()).all()')
code = code.replace('BusSchedule.objects().order_by("-departure_time")', 'BusSchedule.query.order_by(BusSchedule.departure_time.desc()).all()')

code = code.replace('City.objects(is_active=True)', 'City.query.filter_by(is_active=True).all()')
code = code.replace('Bus.objects(is_active=True)', 'Bus.query.filter_by(is_active=True).all()')
code = code.replace('Route.objects(is_active=True)', 'Route.query.filter_by(is_active=True).all()')

code = code.replace('.objects(status=\'Confirmed\')', '.query.filter_by(status=\'Confirmed\').all()')
code = code.replace('BusSchedule.objects(is_active=True).count()', 'BusSchedule.query.filter_by(is_active=True).count()')

# .objects(key=val).first()
code = re.sub(r'([A-Za-z]+)\.objects\((.*?)\)\.first\(\)', r'\1.query.filter_by(\2).first()', code)

# fix stray pass with commit
code = code.replace('    pass\n', '    db.session.commit()\n')

# replace .save()
code = re.sub(r'([a-zA-Z0-9_]+)\.save\(\)', r'db.session.add(\1)\n    db.session.commit()', code)

with open('backend/app/admin/routes.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Done!')
