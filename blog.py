from app import create_app, db
import os
from flask_migrate import Migrate
from flask_login import current_user
from app.main.models import *
from datetime import timedelta
from flask_migrate import upgrade, migrate, init

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()

@app.cli.command()
def deploy():
    init()
    migrate()
    upgrade()
    Role.insert_roles()
    Category.default_categories()
    u = User(username='root', password='rootroot', unread=0, role=Role.query.filter_by(name='Admin').first(), email='adminemail@example.com')
    db.session.add(u)
    db.session.commit()

#--------------------Testing--------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
