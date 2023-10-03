FROM centos/python-38-centos7

LABEL description="coldfront"

USER root

# TODO: comment out these lines if flag_mou_generation_enabled=False
RUN mkdir /root/.ssh && ssh-keyscan github.com > /root/.ssh/known_hosts
COPY --chmod=0600 bootstrap/development/id_coldfront /root/.ssh/id_rsa
RUN pip install git+ssh://git@github.com/ucb-rit/mou-generator.git

WORKDIR /root
COPY requirements.txt ./
RUN pip install -r requirements.txt && rm requirements.txt
RUN pip install jinja2 pyyaml
RUN yum -y install https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.centos7.x86_64.rpm

# mybrc or mylrc
ARG PORTAL="mybrc"
RUN mkdir -p /var/log/user_portals/cf_${PORTAL} \
 && touch /var/log/user_portals/cf_${PORTAL}/cf_${PORTAL}_{portal,api}.log \
 && chmod 775 /var/log/user_portals/cf_${PORTAL} \
 && chmod 664 /var/log/user_portals/cf_${PORTAL}/cf_${PORTAL}_{portal,api}.log

WORKDIR /vagrant/coldfront_app/coldfront/

CMD ./manage.py initial_setup \
 && ./manage.py add_accounting_defaults \
 && ./manage.py create_allocation_periods \
 && ./manage.py add_allowance_defaults \
 && ./manage.py add_directory_defaults \
 && ./manage.py create_staff_group \
 && ./manage.py collectstatic --noinput \
 && ./manage.py runserver 0.0.0.0:80

EXPOSE 80
STOPSIGNAL SIGINT
