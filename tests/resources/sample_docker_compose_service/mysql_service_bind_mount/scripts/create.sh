mysql_ready() {
        mysqladmin ping --host=mysql_service --user=root --password=root_password_42 > /dev/null 2>&1
    }

while !(mysql_ready)
    do
       sleep 3
    done

mysql -u "root" -p"root_password_42" "test_database" -e \
    "CREATE TABLE IF NOT EXISTS test (id INT AUTO_INCREMENT, value INT, PRIMARY KEY (id));INSERT INTO test(value) SELECT 42 WHERE NOT EXISTS (SELECT * FROM test);"

# mysql -u "root" -p"root_password_42" "test_database" -e \
#     "CREATE TABLE test (id INT AUTO_INCREMENT, value INT, PRIMARY KEY (id));INSERT INTO test(value) VALUES(42);"