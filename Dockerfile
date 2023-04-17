FROM centos/python-38-centos7

LABEL description="coldfront"

USER root
WORKDIR /root
COPY requirements.txt ./
RUN pip install -r requirements.txt \
 && pip install jinja2 pyyaml && rm requirements.txt

# mybrc or mylrc
ARG portal="mybrc"
RUN mkdir -p /var/log/user_portals/cf_${portal} \
 && touch /var/log/user_portals/cf_${portal}/cf_${portal}_{portal,api}.log \
 && chmod 775 /var/log/user_portals/cf_${portal} \
 && chmod 664 /var/log/user_portals/cf_${portal}/cf_${portal}_{portal,api}.log

COPY . /vagrant/coldfront_app/coldfront/
WORKDIR /vagrant/coldfront_app/coldfront/

RUN chmod +x ./manage.py

CMD ./manage.py initial_setup \
 && ./manage.py migrate \
 && ./manage.py add_accounting_defaults \
 && ./manage.py add_allowance_defaults \
 && ./manage.py add_directory_defaults \
 && ./manage.py create_allocation_periods \
 && ./manage.py create_staff_group \
 && ./manage.py collectstatic --noinput \
 && ./manage.py runserver 0.0.0.0:80

EXPOSE 80
STOPSIGNAL SIGINT
