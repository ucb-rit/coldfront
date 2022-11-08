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
    "SELECT email, first_name, last_name from auth_user" \
    | grep -v 'email.*first_name.*last_name' | grep -v '^$' | \
    while read line; do
        email=$(echo $line | cut -d'|' -f1 | xargs echo)
        first_name=$(echo $line | cut -d'|' -f2 | xargs echo)
        last_name=$(echo $line | cut -d'|' -f3 | xargs echo)
        dept=''
        dept_name=''

        while read line; do
            if [[ $(echo $line | grep berkeleyEduPrimaryDeptUnit | wc -l) -gt 0 ]]; then
                dept=$(echo $line | cut -d' ' -f2 | xargs echo)
            elif [[ $(echo $line | grep berkeleyEduUnitHRDeptName | wc -l) -gt 0 ]]; then
                dept_name=$(echo $line | cut -d' ' -f2 | xargs echo)
            fi
        done < <(ldapsearch -LLL -H ldaps://ldap.berkeley.edu \
                   -x -D "ou=people,dc=berkeley,dc=edu" \
                   "(&(objectClass=person)(mail=$email))" \
                   berkeleyEduPrimaryDeptUnit berkeleyEduUnitHRDeptName \
                   | grep -v '^$' | grep -v '^dn:')

        if [[ "$dept" == "" || "$dept_name" == "" ]]; then
            while read line; do
                if [[ $(echo $line | grep berkeleyEduPrimaryDeptUnit | wc -l) -gt 0 ]]; then
                    dept=$(echo $line | cut -d' ' -f2 | xargs echo)
                elif [[ $(echo $line | grep berkeleyEduUnitHRDeptName | wc -l) -gt 0 ]]; then
                    dept_name=$(echo $line | cut -d' ' -f2 | xargs echo)
                fi
            done < <(ldapsearch -LLL -H ldaps://ldap.berkeley.edu \
                       -x -D "ou=people,dc=berkeley,dc=edu" \
                       "(&(objectClass=person)(givenName=$first_name)(sn=$last_name))" \
                       berkeleyEduPrimaryDeptUnit berkeleyEduUnitHRDeptName \
                       | grep -v '^$' | grep -v '^dn:')
        fi
        if [[ "$dept" == "" || "$dept_name" == "" ]]; then
            echo "No department or deptartment name found for \
$email ($first_name $last_name)"
        fi
        if [[ "$dept" != "" || "$dept_name" != "" ]]; then
            echo "$email $first_name,$last_name -> \"$dept\",\"$dept_name\""
        fi
    done
