from setuptools import setup

setup(name="proxpy",
    version="0.1",
    description="HTTP/HTTPS proxy server in Python.",
    packages=['proxpy'],
    entry_points={
        'console_scripts':
            ['proxpy=proxpy.proxpy:main']
    }
)
