stadi
--------

The module contains the code to formulate and solve the *static bike sharing rebalancing problem with demand intervals* (SBRP-DI). We have named the module as stadi for easier pronunciation. The module is used to generate the results presented in the manuscript:

- Ikonen, T. J., Heljanko, K., Harjunkoski, I. (2022). A generalized disjunctive programming model for the static bike sharing rebalancing problem with demand intervals (submitted).

The module includes an implementation of the queueing system based prediction method, the clustering model, and the routing model by Schuijbroek et al. (2017). See the reference for further details.

The results have been generated on a high performance computing facility (HPC). The results can also be reproduced on a standard laptop but may take a long computing time.

# Installation

The code uses [graph-tool](https://graph-tool.skewed.de/) in the identification of separations. The instructions to install graph-tool can be found [here](https://git.skewed.de/count0/graph-tool/-/wikis/installation-instructions).

The code uses [cartopy](https://scitools.org.uk/cartopy/docs/latest/index.html#) in plotting routes and stations on a map. The instructions to install cartopy can be found [here](https://scitools.org.uk/cartopy/docs/latest/installing.html).

If you are using conda, you may use the following commands to install these two dependencies into a new environment:

    $ conda create --name stadi_env python=3.9
    $ conda activate stadi_env
    $ conda install -c conda-forge graph-tool cartopy

The code uses [Gurobi](https://www.gurobi.com/) as the MIP solver. Academics can apply for a [free license](https://www.gurobi.com/academia/academic-program-and-licenses/).

After installing the above-mentioned dependencies, obtaining a Gurobi license, and cloning the repository, you can use the following commands to install stadi:

    $ cd stadi/
    $ pip install -e .

# Package versions

We have developed the module using Python 3.9 and the following versions of the main dependencies:

- cartopy 0.19.0
- Gurobi 9.1.2
- graph-tool 2.37
- matplotlib-base 3.4.2
- numpy 1.20.2
- pandas 1.2.4
- scipy 1.6.3


# Benchmark instances

The benchmark instance with demand intervals are proposed by Erdogan et al. (2014). The authors propose a transformation of the benchmarks instances by Hernández-Pérez & Salazar-González (2007), which do not have demand intervals. The original benchmarks are are available at http://hhperez.webs.ull.es/PDsite/. Dr. Hipólito Hernández-Pérez has kindly given us the permission to include these instances in this module. The instances can be found from the folder data/hernandez_perez07/.

The following commands reproduce the benchmarks with 50 stations and demand interval of q - p = 5:

    $ cd benchmarks/
    $ python preprocessRun.py 210
    $ python multiexecute.py 210 hull_pm_general
    $ python readResults.py 210 hull_pm_general

Estimated runtime of the third command (multiexecute.py) is roughly one hour on a standard laptop. These results correspond to the right most column of Table 1 in Ikonen et al. (2022). See the run record in benchmarks/runRecord.txt for a description of other results. The final results are also included as .zip files in the folder benchmarks/runs.

# Test cases from Helsinki

The test cases are based on data recorded in the bike sharing system in Helsinki, Finland. The following data sources are used (all of which are published under the [Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)) license:

- Helsinki Region Transport (HSL) (2016a). City bike stations’ Origin-Destination (OD) data [accessed on November 3, 2020]. https://www.avoindata.fi/data/en_GB/dataset/helsingin-ja-espoon-kaupunkipyorilla-ajatut-matkat

- Helsinki Region Transport (HSL) (2016b). Helsinki Region Transport’s (HSL) city bicycle stations [accessed on November 3, 2020]. https://www.avoindata.fi/data/en_GB/dataset/hsl-n-kaupunkipyoraasemat.

- Kainu, M. (2017). Helsingin kaupunkipyörät: Avoin data telinekohtaisista vapaiden pyörien määristä kausilta 2017, 2018, 2019, 2020 ja 2021 [accessed on February 22, 2021]. https://data.markuskainu.fi/opendata/kaupunkipyorat/.

The data can be found from the folder data/helsinki/. The following commands reproduce the results of region A / 6-9 am with the GDP model in Table 4 in Ikonen et al. (2022):

    $ cd helsinki/
    $ python fetchSnapshots.py 2021-06 2021-08
    $ python preprocessCase.py 50
    $ python preprocessRun.py 50 1
    $ python execute.py 50 1 hull_pm_general
    $ python postprocessRun.py 50 1

The estimated runtime of the fifth command (execute.py) is roughly one minute on a standard laptop. In order to run the reference method, you can use the following command (the estimated runtime is roughly four hours on a standard laptop):

    $ python execute.py 50 1 sch17

See the run record in helsinki/runRecord.txt for a description of other results. The final results are also included as .zip files in the folder helsinki/cases.

# References

- Hernández-Pérez, H., & Salazar-González, J.-J. (2007). The one-commodity pickup-and-delivery traveling salesman
problem: Inequalities and algorithms. *Networks: An International Journal*, 50, 258–272.

- Erdoğan, G., Laporte, G., & Wolfler Calvo, R. (2014). The static bicycle relocation problem with demand intervals.
*European Journal of Operational Research*, 238 , 451–457.

- Schuijbroek, J., Hampshire, R. C., & Van Hoeve, W.-J. (2017). Inventory rebalancing and vehicle routing in bike
sharing systems. *European Journal of Operational Research*, 257 , 992–1004.

- Ikonen, T. J., Heljanko, K., & Harjunkoski, I. (2022). A generalized disjunctive programming model for the static bike sharing rebalancing problem with demand intervals (submitted).