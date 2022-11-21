#!/usr/bin/env bash
shopt -s extglob
echo -n "email,first_name,last_name,dept_unit,dept_unit_hierarchy,"
echo "dept_unit_desc,dept_num,dept_num_hierarchy,dept_num_desc"
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
        dept_unit=""
        dept_name=""
        dept_unit_hierarchy=""
        dept_unit_desc=""
        dept_num=()
        dept_num_hierarchy=()
        dept_num_desc=()

        for filter in "(mail=$email)" "(givenName=$first_name)(sn=$last_name)"; do
            while read line; do
                if [[ $(echo $line | grep berkeleyEduPrimaryDeptUnit | wc -l) -gt 0 ]]; then
                    dept_unit=$(echo $line | cut -d' ' -f2- | xargs -0 echo)
                elif [[ $(echo $line | grep berkeleyEduUnitHRDeptName | wc -l) -gt 0 ]]; then
                    dept_name=$(echo $line | cut -d' ' -f2- | xargs -0 echo)
                elif [[ $(echo $line | grep departmentNumber | wc -l) -gt 0 ]]; then
                    var="$(echo $line | cut -d' ' -f2- | xargs -0 echo)"
                    var="${var##*( )}"
                    var="${var%%*( )}"
                    dept_num+=("$var")
                fi
            done < <(ldapsearch -LLL -H ldaps://ldap.berkeley.edu \
                    -x -D "ou=,dc=berkeley,dc=edu" \
                    "(&(objectClass=person)$filter)" \
                    berkeleyEduPrimaryDeptUnit berkeleyEduUnitHRDeptName \
                    departmentNumber | grep -v '^$' | grep -v '^dn:')
            if [[ "$dept_unit" != "" ]]; then
                break 1
            fi
        done

        if [[ "$dept_unit" != "" ]]; then
            while read line; do
                if [[ $(echo $line | grep berkeleyEduOrgUnitHierarchyString | wc -l) -gt 0 ]]; then
                    dept_unit_hierarchy="$(echo $line | cut -d' ' -f2- | xargs -0 echo)"
                elif [[ $(echo $line | grep description | wc -l) -gt 0 ]]; then
                    dept_unit_desc="$(echo $line | cut -d' ' -f2- | xargs -0 echo)"
                fi
            done < <(ldapsearch -LLL -H ldaps://ldap.berkeley.edu \
                    -x -D "ou=people,dc=berkeley,dc=edu" \
                    "(&(objectClass=organizationalunit)(ou=$dept_unit))" \
                    berkeleyEduOrgUnitHierarchyString description \
                    | grep -v '^$' | grep -v '^dn:')
            
            for num in $dept_num; do
                while read line; do
                    if [[ $(echo $line | grep berkeleyEduOrgUnitHierarchyString | wc -l) -gt 0 ]]; then
                        var=$(echo $line | cut -d' ' -f2- | xargs -0 echo)
                        var="${var##*( )}"
                        var="${var%%*( )}"
                        dept_num_hierarchy+=("$var")
                    elif [[ $(echo $line | grep description | wc -l) -gt 0 ]]; then
                        var=$(echo $line | cut -d' ' -f2- | xargs -0 echo)
                        var="${var##*( )}"
                        var="${var%%*( )}"
                        dept_num_desc+=("$var")
                    fi
                done < <(ldapsearch -LLL -H ldaps://ldap.berkeley.edu \
                        -x -D "ou=people,dc=berkeley,dc=edu" \
                        "(&(objectClass=organizationalunit)(ou=$num))" \
                        berkeleyEduOrgUnitHierarchyString description \
                        | grep -v '^$' | grep -v '^dn:')
            done
        fi
        
        for var in "email" "first_name" "last_name" "dept_unit" "dept_name" \
                   "dept_num" "dept_unit_hierarchy" "dept_unit_desc" \
                   "dept_num_hierarchy" "dept_num_desc"; do
            eval "$var=\"\${$var##*( )}\""
            eval "$var=\"\${$var%%*( )}\""
        done

        IFS=","
        echo -n "$email,$first_name,$last_name,"
        echo -n "$dept_unit,$dept_unit_hierarchy,$dept_unit_desc"
        if [[ "$dept_num" != "" ]]; then
            echo ",\"$dept_num\",\"$dept_num_hierarchy\",\"$dept_num_desc\""
        else
            echo ",,,"
        fi
    done
