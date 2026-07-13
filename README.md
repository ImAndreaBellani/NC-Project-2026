# NC-Project-2026
Repository of NETWORK COMPUTING Lab Project. Authors: Andrea Bellani, Andrea Migliorini

<table>
  <tr>
    <th>Paper selected</th>
    <th>Y. Li et al. : HPCC: High Precision Congestion Control. In SIGCOMM '19, August 19–23, 2019, Beijing, China, © 2019 Association for Computing Machinery.</th>
  </tr>
  <tr>
    <th>Results reproduced</th>
    <th>Figures 11 and 14</th>
  </tr>
  <tr>
    <th>Research question investigated </th>
    <th>Testing CC algorithms on different traffic distributions</th>
  </tr>
</table>

## Project structure
- `/HPCC` : contains our copy of HPCC replication package (pulled from [alibaba-edu/High-Precision-Congestion-Control](https://github.com/alibaba-edu/High-Precision-Congestion-Control)) to which we added our `traffic_gen/traffic_gen_incast.py` script to generate flows with incasts events;
- `/REPORT` : contains our project report;
- `/Trace visualizer` : contains all the scripts we implemented for our performance evaluation.
