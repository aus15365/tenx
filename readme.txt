This is instrution how to run this package.

1. setup proper python path.

    The package is in a folder named "tenx", so whereever the pachage is put the path should be set to that,

    For example,

    /home/jchen/testing/tenx

    then following path should be set

    export PYTHONPATH=/home/jchen/testing/tenx

2. the pachage also contains an unit testing profile under folder tenx/tests, the unit testing can be run byt

    cd /home/jchen/testing/tenx
    nosetests -sv .

3. A demo method is also provided in module exchange.py to show how to run the system.

   when entering "exit" as input, the demo will end.



