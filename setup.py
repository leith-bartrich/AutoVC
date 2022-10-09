from setuptools import setup

setup(
    name='AutoVC',
    version='0.1.0',
    packages=['autovc_cirkis'],
    url='',
    license='MIT',
    author='',
    author_email='',
    description='FIE Cirkis Branch of AutoVC',
    entry_points = {
        'console_scripts': [
            'autovc_train = autovc_cirkis.cli.train:cli',
            'autovc_preprocess = autovc_cirkis.cli.preprocess:cli',
            'autovc_inference = autovc_cirkis.cli.inference:cli',
        ]
    },
)
