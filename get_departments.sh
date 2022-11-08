# Search through all users as so:
# ldapsearch -LLL -H ldaps://ldap.berkeley.edu \
#            -x -D "ou=people,dc=berkeley,dc=edu" \
#                  "(&(objectClass=person)(mail=sahai@eecs.berkeley.edu))"
#                  berkeleyEduPrimaryDeptUnit berkeleyEduUnitHRDeptName
# If an email is not found, then search using name::w
# ldapsearch -LLL -H ldaps://ldap.berkeley.edu \
#            -x -D "ou=people,dc=berkeley,dc=edu" \
#                  "(&(objectClass=person)(givenName=Anant)(sn=Sahai))" \
#                  berkeleyEduPrimaryDeptUnit berkeleyEduUnitHRDeptName
# Print out berkeleyEduPrimaryDeptUnit and berkeleyEduUnitHRDeptName

sudo -u postgres psql -d cf_brc_db -c \
    "SELECT ea.email, au.first_name, au.last_name \
    FROM project_projectuser AS pu INNER JOIN auth_user AS au ON \
     pu.user_id=au.id INNER JOIN user_emailaddress AS ea ON au.id = ea.user_id \
    WHERE pu.role_id=3 AND ea.email LIKE '%berkeley.edu'" | \
    grep -v 'email.*first_name.*last_name' | grep -v '^[-+]*$' | \
    while read line; do
        email=$(echo $line | cut -d'|' -f1 | xargs -0 echo)
        first_name=$(echo $line | cut -d'|' -f2 | xargs -0 echo)
        last_name=$(echo $line | cut -d'|' -f3 | xargs -0 echo)
        dept=''
        dept_name=''

        while read line; do
            if [[ $(echo $line | grep berkeleyEduPrimaryDeptUnit | wc -l) -gt 0 ]]; then
                dept=$(echo $line | cut -d' ' -f2- | xargs -0 echo)
            elif [[ $(echo $line | grep berkeleyEduUnitHRDeptName | wc -l) -gt 0 ]]; then
                dept_name=$(echo $line | cut -d' ' -f2- | xargs -0 echo)
            fi
        done < <(ldapsearch -LLL -H ldaps://ldap.berkeley.edu \
                   -x -D "ou=people,dc=berkeley,dc=edu" \
                   "(&(objectClass=person)(mail=$email))" \
                   berkeleyEduPrimaryDeptUnit berkeleyEduUnitHRDeptName \
                   | grep -v '^$' | grep -v '^dn:')

        if [[ "$dept" == "" || "$dept_name" == "" ]]; then
            while read line; do
                if [[ $(echo $line | grep berkeleyEduPrimaryDeptUnit | wc -l) -gt 0 ]]; then
                    dept=$(echo $line | cut -d' ' -f2- | xargs -0 echo)
                elif [[ $(echo $line | grep berkeleyEduUnitHRDeptName | wc -l) -gt 0 ]]; then
                    dept_name=$(echo $line | cut -d' ' -f2- | xargs -0 echo)
                fi
            done < <(ldapsearch -LLL -H ldaps://ldap.berkeley.edu \
                       -x -D "ou=people,dc=berkeley,dc=edu" \
                       "(&(objectClass=person)(givenName=$first_name)(sn=$last_name))" \
                       berkeleyEduPrimaryDeptUnit berkeleyEduUnitHRDeptName \
                       | grep -v '^$' | grep -v '^dn:')
        fi

        if [[ "$dept" == "" && "$dept_name" == "" ]]; then
            echo -e "No department or department name found for\t\t$email\t\t$first_name\t\t$last_name"
        elif [[ "$dept" == "" ]]; then
            echo -e "No department ONLY found for\t\t$email\t\t$first_name\t\t$last_name"
        elif [[ "$dept_name" == "" ]]; then
            echo -e "No department name ONLY found for\t\t$email\t\t$first_name\t\t$last_name"
        fi
        
        if [[ "$dept" != "" || "$dept_name" != "" ]]; then
            echo -e "$email\t\t$first_name\t\t$last_name\t\t${dept:-NOT FOUND}\t\t${dept_name:-NOT FOUND}"
        fi
    done
