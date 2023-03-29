FROM centos/python-38-centos7

LABEL description="coldfront"

USER root
WORKDIR /root
COPY requirements.txt ./
RUN pip install -r requirements.txt \
 && pip install jinja2 pyyaml && rm requirements.txt

RUN mkdir -p /vagrant/coldfront_app
WORKDIR /vagrant/coldfront_app/
RUN git clone -b issue_521 https://github.com/ucb-rit/coldfront.git
WORKDIR ./coldfront
COPY main.yml ./main.yml

RUN mkdir -p /var/log/user_portals/cf_mybrc \
 && touch /var/log/user_portals/cf_mybrc/cf_mybrc_{portal,api}.log \
 && chmod 775 /var/log/user_portals/cf_mybrc \
 && chmod 664 /var/log/user_portals/cf_mybrc/cf_mybrc_{portal,api}.log \
 && chmod +x ./manage.py

RUN cp coldfront/config/local_settings.py.sample \
       coldfront/config/local_settings.py \
 && cp coldfront/config/local_strings.py.sample \
       coldfront/config/local_strings.py \
 && python -c \
"from jinja2 import Template, Environment, FileSystemLoader; \
import yaml; \
env = Environment(loader=FileSystemLoader('bootstrap/ansible/')); \
env.filters['bool'] = lambda x: str(x).lower() in ['true', 'yes', 'on', '1']; \
options = yaml.safe_load(open('main.yml').read()); \
options.update({'redis_host': 'redis', 'db_host': 'db'}); \
print(env.get_template('settings_template.tmpl').render(options))" \
                                        > coldfront/config/dev_settings.py

CMD ./manage.py initial_setup \
 && ./manage.py migrate \
 && ./manage.py add_accounting_defaults \
 && ./manage.py add_allowance_defaults \
 && ./manage.py add_directory_defaults \
 && ./manage.py create_allocation_periods \
 && ./manage.py create_staff_group \
 && ./manage.py collectstatic \
 && ./manage.py runserver 0.0.0.0:80

EXPOSE 80
STOPSIGNAL SIGINT
