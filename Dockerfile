FROM centos/python-38-centos7

LABEL description="coldfront"


# install dependencies
# RUN yum -y install epel-release
# RUN yum -y update
# RUN yum -y install python36 python36-devel git memcached redis

USER root
WORKDIR /root

# install coldfront
RUN mkdir -p /vagrant/coldfront_app
WORKDIR /vagrant/coldfront_app/
RUN git clone -b issue_521 https://github.com/ucb-rit/coldfront.git
WORKDIR ./coldfront
COPY main.yml ./main.yml

RUN pip3 install wheel jinja2-cli pyyaml \
 && pip3 install -r requirements.txt

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
options.update({'redis_host': 'redis', 'db_host': 'db', \
                'debug_toolbar_ips':['host.docker.internal']}); \
print(env.get_template('settings_template.tmpl').render(options))" \
                                        > coldfront/config/dev_settings.py

RUN mkdir -p /var/log/user_portals/cf_mybrc \
 && touch /var/log/user_portals/cf_mybrc/cf_mybrc_{portal,api}.log \
 && chmod 775 /var/log/user_portals/cf_mybrc \
 && chmod 664 /var/log/user_portals/cf_mybrc/cf_mybrc_{portal,api}.log \
 && chmod +x ./manage.py


CMD ./manage.py initial_setup \
 && ./manage.py runserver

EXPOSE 8080
STOPSIGNAL SIGINT
