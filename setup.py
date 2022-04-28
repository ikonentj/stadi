from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='hullbikes',
      version='0.1',
      description='',
      long_description=readme(),
      classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 3.8',
        'Topic :: Scientific/Engineering',
      ],
      keywords='"bike sharing rebalancing" "routing" "optimization"',
      url='',
      author='Teemu J. Ikonen',
      author_email='teemu.ikonen@aalto.fi',
      license='GNU',
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

