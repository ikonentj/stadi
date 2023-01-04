from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='hullbikes',
      version='0.1',
      description='',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: Apache License, Version 2.0',
        'Programming Language :: Python :: 3.9',
        'Topic :: Scientific/Engineering',
      ],
      keywords='"bike sharing rebalancing" "routing" "optimization"',
      url='',
      author='Teemu J. Ikonen',
      author_email='teemu.ikonen@aalto.fi',
      license='Apache 2.0',
      packages=['SBRP_DI'],
      package_dir={},
      install_requires=[
                        'numpy',
                        'matplotlib',
                        'pandas',
                        'tqdm',
                        'gurobipy',
                        'geopy'
                       ],
      include_package_data=True,
      zip_safe=False,
      test_suite='nose.collector',
      tests_require=['nose'],
)

