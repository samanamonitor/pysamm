from setuptools import setup, find_packages
from samm import __version__
import re, os

def set_control_version():
    with open("./debian/control.tmpl", "r") as src, open("./debian/control", "w") as dst:
        while True:
            datain = src.readline()
            if len(datain) == 0: break
            dataout = re.sub(r"%VERSION%", __version__, datain)
            dst.write(dataout)

if __name__ == "__main__":
    set_control_version()
    setup(
        name='samm',
        version=__version__,
        packages=find_packages(include=['samm', 'samm.*']),
        scripts=[
            'scripts/server.py',
            'scripts/scheduler.py',
            'scripts/collector.py'
            ],
        data_files=[
            ('/usr/local/samm/etc', [
                'docs/examples/conf.json.example',
                'docs/examples/resources.json.example']
            ),
            ('/usr/local/samm/etc/objects', 
                list(map(lambda x: 'docs/examples/objects/' + x, os.listdir('docs/examples/objects/')))
            ),
            ('/usr/share/samm', [ 'requirements.txt' ] )
        ],
        install_requires=[ 
            "flask",
            "icmplib",
            "python-ldap",
            "requests",
            "pika",
            "opentelemetry-exporter-prometheus-remote-write"
        ]
    )
