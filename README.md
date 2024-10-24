# XyTable

This is a demo utilizing [Zeugwerk Framewerk](https://doc.zeugwerk.dev) and [Struckig](https://github.com/stefanbesler/Struckig) to writing text on a XY table with a pneumatic actuator that holds a pen (laser-cutter or similar) and two motors to move the pen.

A C# program is capturing input of a user and splits every character that is typed into segments of lines and splines. The segments are sent to a Beckhoff PLC via an ADS client.
On the PLC side, depending on the segment type, either straight lines are drawn or centripetal `Catmull–Rom splines` are calculated for the segment. The trajectory of the x- and y-axis are phase-synchronized with Struckig and the interpolated mode is used to send the current target position and velocity to both drives.


<div style="display: flex; justify-content: space-between;">
<img src="/Images/Peek 2024-10-24 21-05.gif"/>
</div>

## Requirements

To run this application, ensure you have the following installed:

- [TwinCAT]() >= 4024.xx
- [Zeugwerk Development Kit](https://doc.zeugwerk.dev/) >= 1.6
- Python 3.x (We recommend [Miniconda](https://docs.anaconda.com/miniconda/))


## Visualization

To run the Visualization in Windows a python distribution has to be installed (Anaconda or Miniconda is recommended).
With an installed python distribution, execute the following commands in the `Visualization` folder to prepare a virtual environment for python and install all requirements

```bash
pip install virtualenv
virtualenv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Activate the PLC and run the Visualization with 

```bash
python main.py
```

You can use the `Servicepanel`, which is integrated into Zeugwerk Creator to control the PLC.
