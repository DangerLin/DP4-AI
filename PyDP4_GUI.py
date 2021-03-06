#!/usr/bin/env python
from PyQt5 import QtWidgets, QtCore, QtGui
import time
import os
import PyDP4
import queue
import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np
from scipy.stats import norm
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from rdkit.Chem import AllChem as Chem
from rdkit.Chem import Draw
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D
import pickle

from pathlib import Path


class Window(QtWidgets.QMainWindow):
    # create signal to start background job

    signal_start_PyDP4 = QtCore.pyqtSignal()

    # signal_finished_PyDP4 = QtCore.pyqtSignal()

    def __init__(self):
        super(Window, self).__init__()

        self.table_widget = TabWidget(self)
        self.setCentralWidget(self.table_widget)

        # self.tabs.currentChanged.connect(self.onChange)  # changed!

        self.show()

        # check if DP4outfile is there


class TabWidget(QtWidgets.QWidget):

    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.layouttabs = QtWidgets.QVBoxLayout(self)

        # Initialize tab screen
        self.tabs = QtWidgets.QTabWidget()
        self.tab1 = QtWidgets.QWidget()

        self.Tab1 = CalculationTab()

        # Add tabs
        self.tabs.addTab(self.tab1, "Calculation")

        self.tab1.layout = QtWidgets.QVBoxLayout()
        self.tab1.layout.addWidget(self.Tab1)
        self.tab1.setLayout(self.tab1.layout)

        # Add tabs to widget
        self.layouttabs.addWidget(self.tabs)
        self.setLayout(self.layouttabs)

    def addplottabs(self):

        self.tab2 = QtWidgets.QWidget()
        self.tab3 = QtWidgets.QWidget()
        self.tab4 = QtWidgets.QWidget()
        self.tab5 = QtWidgets.QWidget()

        self.tabs.addTab(self.tab2, "Proton Plot")
        self.tabs.addTab(self.tab3, "Carbon Plot")

        self.Tab2 = ProtonPlotTab()
        self.Tab3 = CarbonPlotTab()
        self.Tab4 = StatsTab()
        self.Tab5 = ConformerTab()
        
        if 's' in ui.table_widget.Tab1.settings.Workflow:
            self.tabs.addTab(self.tab4, "Stats")
            self.tab4.layout = QtWidgets.QVBoxLayout(self)
            self.tab4.layout.addWidget(self.Tab4)
            self.tab4.setLayout(self.tab4.layout)

        self.tabs.addTab(self.tab5, "Conformers")

        self.tab2.layout = QtWidgets.QVBoxLayout(self)
        self.tab2.layout.addWidget(self.Tab2)
        self.tab2.setLayout(self.tab2.layout)

        self.tab3.layout = QtWidgets.QVBoxLayout(self)
        self.tab3.layout.addWidget(self.Tab3)
        self.tab3.setLayout(self.tab3.layout)



        self.tab5.layout = QtWidgets.QVBoxLayout(self)
        self.tab5.layout.addWidget(self.Tab5)
        self.tab5.setLayout(self.tab5.layout)

        self.layouttabs.addWidget(self.tabs)
        self.setLayout(self.layouttabs)

        ui.update()


class StatsTab(QtWidgets.QWidget):

    def __init__(self):

        super(StatsTab, self).__init__()

        self.setFixedSize(876, 875)

        self.layout = QtWidgets.QGridLayout()

        self.setLayout(self.layout)

        # add isomer selection

        self.IsomerSelect = QtWidgets.QComboBox(self)

        self.Isomers = ui.table_widget.Tab1.worker.Isomers

        self.dp4data = ui.table_widget.Tab1.worker.DP4Data

        self.IsomerSelect.addItems(self.Isomer_number())

        # make error table

        # populate table based on the Isomer selected

        self.Hplot = plotstats('H')

        self.IsomerSelect.currentIndexChanged.connect(self.Hplot.populatetable)

        self.layout.addWidget(self.Hplot.errortable ,0 ,0)

        self.layout.addWidget(self.Hplot.statscanvas ,0 ,1)

        self.Cplot = plotstats('C')

        self.IsomerSelect.currentIndexChanged.connect(self.Cplot.populatetable)

        self.layout.addWidget(self.Cplot.errortable ,2 ,0)

        self.layout.addWidget(self.Cplot.statscanvas ,2 ,1)

        self.layout.setColumnStretch(0 ,4)
        self.layout.setColumnStretch(1, 5)

        self.layout.setContentsMargins(0, 50, 0, 0)

    def Isomer_number(self):

        Isomer_list = []

        for c, i in enumerate(self.Isomers):
            Isomer_list.append("Isomer " + str(c + 1))

        return Isomer_list


class plotstats(QtWidgets.QWidget):

    def __init__(self ,Atom):

        super(plotstats, self).__init__()

        # when a cell is selected signal to plot stats

        self.atom = Atom

        self.findmeans()

        self.dp4data = ui.table_widget.Tab1.worker.DP4Data

        self.Isomers = ui.table_widget.Tab1.worker.Isomers

        self.errortable = QtWidgets.QTableWidget(self)

        # self.errortable.setGeometry(QtCore.QRect(10, 50,400, 400))

        self.errortable.setColumnCount(5)

        self.errortable.setHorizontalHeaderLabels(["Atom Label" ,"Calc Shift" ,"Scaled" ,"Exp" ,"Error"])

        self.errortable.setColumnWidth(0, 70)
        self.errortable.setColumnWidth(1, 70)
        self.errortable.setColumnWidth(2, 70)
        self.errortable.setColumnWidth(3, 70)
        self.errortable.setColumnWidth(4, 70)

        self.statsfigure = Figure()

        self.statscanvas = FigureCanvas(self.statsfigure)

        # self.errortable.cellClicked.connect(self.plot)

        self.errortable.itemSelectionChanged.connect(self.plot)

        self.statscanvas.mpl_connect('button_press_event', self.selectpoint)

    def plot(self):

        r = int(self.errortable.currentRow())

        if r >= 0:

            error = float(self.errortable.item(r, 4).text())

            # decide which stats params have been used

            self.statsfigure.clear()

            self.statsfig = self.statsfigure.add_subplot(111)

            if self.atom =='H':

                m = abs(max([item for sublist in self.dp4data.Herrors for item in sublist] ,key= abs))

            elif self.atom =='C':
                m = abs(max([item for sublist in self.dp4data.Cerrors for item in sublist], key=abs))

            # plot all errors at low transparency

            for e in self.errors:

                self.statsfig.plot([e, e], [0, self.multipdf([float(e)])], color='C1' ,alpha = 0.5)

                self.statsfig.plot(e, self.multipdf([float(e)]), 'o', color='C1' ,alpha = 0.5)

            x = np.linspace(- 2* m, 2 * m, 1000)

            self.statsfig.plot(x, self.multipdf(x))

            self.statsfig.plot([error, error], [0, self.multipdf([float(error)])], color='red', alpha=0.75)

            self.statsfig.plot(error, self.multipdf([float(error)]), 'o', color='red', alpha=0.75)

            self.statsfig.set_xlim([x[0], x[-1]])

            self.statsfig.set_xlabel("error (ppm)")

            self.statsfig.set_ylabel("probability density")

            self.statscanvas.draw()

    def multipdf(self, x):

        y = np.zeros(len(x))

        if self.atom == 'H':

            for mean, std in zip(self.Hmeans, self.Hstdevs):
                y += norm.pdf(x, loc=mean, scale=std)

        elif self.atom == 'C':

            for mean, std in zip(self.Cmeans, self.Cstdevs):
                y += norm.pdf(x, loc=mean, scale=std)

        return y

    def findmeans(self):


        if ui.table_widget.Tab1.worker.settings.StatsParamFile == 'none':

            self.Hmeans = [0]

            self.Hstdevs = [0.18731058105269952]

            self.Cmeans = [0]

            self.Cstdevs = [2.269372270818724]

        else:

            self.Cmeans, self.Cstdevs, self.Hmeans, self.Hstdevs = ReadParamFile(
                ui.table_widget.Tab1.worker.settings.StatsParamFile, 'g')

    def populatetable(self):

        # which isomer is selected

        self.isomerindex = int(str(ui.table_widget.Tab4.IsomerSelect.currentText())[-1]) - 1

        self.errortable.setRowCount(0)

        if self.atom == 'H':

            self.labels, self.shifts, self.exps, self.scaleds, self.errors = self.dp4data.Hlabels[self.isomerindex], \
                                                                             self.dp4data.Hshifts[self.isomerindex], \
                                                                             self.dp4data.Hexp[self.isomerindex], \
                                                                             self.dp4data.Hscaled[self.isomerindex], \
                                                                             self.dp4data.Herrors[self.isomerindex]

        elif self.atom == 'C':

            self.labels, self.shifts, self.exps, self.scaleds, self.errors = self.dp4data.Clabels[self.isomerindex], \
                                                                             self.dp4data.Cshifts[self.isomerindex], \
                                                                             self.dp4data.Cexp[self.isomerindex], \
                                                                             self.dp4data.Cscaled[self.isomerindex], \
                                                                             self.dp4data.Cerrors[self.isomerindex]

        self.errortable.setRowCount(len(self.labels))

        # set info in rows and columns

        c = 0

        for label, shift, exp, scaled, error in zip(self.labels, self.shifts, self.exps, self.scaleds, self.errors):
            self.errortable.setItem(c, 0, QtWidgets.QTableWidgetItem(label))
            self.errortable.setItem(c, 1, QtWidgets.QTableWidgetItem(str(round(shift, 2))))
            self.errortable.setItem(c, 2, QtWidgets.QTableWidgetItem(str(round(scaled, 2))))
            self.errortable.setItem(c, 3, QtWidgets.QTableWidgetItem(str(round(exp, 2))))
            self.errortable.setItem(c, 4, QtWidgets.QTableWidgetItem(str(round(error, 2))))

            c += 1

        self.errortable.selectRow(0)

        self.plot()

    def selectpoint(self, event):

        self.xpos = event.xdata

        self.ypos = event.ydata

        # find the closest point to the click

        coords = self.statsfig.transData.transform((self.xpos, self.ypos))

        coordinates = np.array(self.statsfig.transData.transform(list(zip(self.errors, self.multipdf(self.errors)))))

        mindis = np.argmin((coordinates[:, 0] - coords[0]) ** 2 + (coordinates[:, 1] - coords[1]) ** 2)

        self.errortable.selectRow(mindis)


class CalculationTab(QtWidgets.QWidget):
    signal_start_PyDP4 = QtCore.pyqtSignal()

    def __init__(self):

        super(CalculationTab, self).__init__()
        self.cwd = Path(os.getcwd())
        #self.log_file = open(self.cwd / "DP4_log.log" , "w+")
        self.setFixedSize(876, 875)
        self.label = QtWidgets.QLabel(self)
        self.label.setGeometry(QtCore.QRect(10, 10, 121, 16))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self)
        self.label_2.setGeometry(QtCore.QRect(10, 140, 57, 15))
        self.label_2.setObjectName("label_2")
        self.solvent_drop = QtWidgets.QComboBox(self)
        self.solvent_drop.setGeometry(QtCore.QRect(120, 240, 101, 31))
        self.solvent_drop.setObjectName("solvent_drop")
        self.DFT_geom_functional_drop = QtWidgets.QComboBox(self)
        self.DFT_geom_functional_drop.setGeometry(QtCore.QRect(370, 240, 101, 31))
        self.DFT_geom_functional_drop.setObjectName("DFT_geom_functional_drop")
        self.DFT_geom_basis_drop = QtWidgets.QComboBox(self)
        self.DFT_geom_basis_drop.setGeometry(QtCore.QRect(370, 300, 101, 31))
        self.DFT_geom_basis_drop.setObjectName("DFT_geom_basis_drop")
        self.label_3 = QtWidgets.QLabel(self)
        self.label_3.setGeometry(QtCore.QRect(370, 220, 81, 16))
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(self)
        self.label_4.setGeometry(QtCore.QRect(370, 280, 81, 16))
        self.label_4.setObjectName("label_4")
        self.Energy_functional_drop = QtWidgets.QComboBox(self)
        self.Energy_functional_drop.setGeometry(QtCore.QRect(490, 240, 101, 31))
        self.Energy_functional_drop.setObjectName("Energy_functional_drop")
        self.label_5 = QtWidgets.QLabel(self)
        self.label_5.setGeometry(QtCore.QRect(490, 280, 81, 16))
        self.label_5.setObjectName("label_5")
        self.Energy_basis_drop = QtWidgets.QComboBox(self)
        self.Energy_basis_drop.setGeometry(QtCore.QRect(490, 300, 101, 31))
        self.Energy_basis_drop.setObjectName("Energy_basis_drop")
        self.label_6 = QtWidgets.QLabel(self)
        self.label_6.setGeometry(QtCore.QRect(490, 220, 81, 16))
        self.label_6.setObjectName("label_6")
        self.label_7 = QtWidgets.QLabel(self)
        self.label_7.setGeometry(QtCore.QRect(610, 280, 81, 16))
        self.label_7.setObjectName("label_7")
        self.NMR_basis_drop = QtWidgets.QComboBox(self)
        self.NMR_basis_drop.setGeometry(QtCore.QRect(610, 300, 101, 31))
        self.NMR_basis_drop.setObjectName("NMR_basis_drop")
        self.label_8 = QtWidgets.QLabel(self)
        self.label_8.setGeometry(QtCore.QRect(610, 220, 81, 16))
        self.label_8.setObjectName("label_8")
        self.NMR_functional_drop = QtWidgets.QComboBox(self)
        self.NMR_functional_drop.setGeometry(QtCore.QRect(610, 240, 101, 31))
        self.NMR_functional_drop.setObjectName("NMR_functional_drop")
        self.label_9 = QtWidgets.QLabel(self)
        self.label_9.setGeometry(QtCore.QRect(120, 220, 81, 16))
        self.label_9.setObjectName("label_9")
        self.Output_box = QtWidgets.QTextEdit(self)
        self.Output_box.setGeometry(QtCore.QRect(0, 460, 875, 415))
        self.Output_box.setObjectName("Output_box")
        self.label_11 = QtWidgets.QLabel(self)
        self.label_11.setGeometry(QtCore.QRect(20, 440, 57, 15))
        self.label_11.setObjectName("label_11")
        self.Stats_list = QtWidgets.QListWidget(self)
        self.Stats_list.setGeometry(QtCore.QRect(730, 330, 121, 91))
        self.Stats_list.setObjectName("Stats_list")
        self.Gobutton = QtWidgets.QPushButton(self)
        self.Gobutton.setGeometry(QtCore.QRect(300, 370, 251, 81))
        self.Gobutton.setObjectName("Gobutton")
        self.Add_stats_model = QtWidgets.QPushButton(self)
        self.Add_stats_model.setGeometry(QtCore.QRect(730, 300, 121, 23))
        self.Add_stats_model.setObjectName("Add_stats_model")
        self.widget = QtWidgets.QWidget(self)
        self.widget.setGeometry(QtCore.QRect(10, 40, 841, 91))
        self.widget.setObjectName("widget")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")

        self.structure_widget = QtWidgets.QWidget(self)
        self.structure_layout = QtWidgets.QVBoxLayout(self)

        self.Add_structure = QtWidgets.QPushButton(self.widget)
        self.Add_structure.setObjectName("Add_structure")
        self.Add_structure.setText("Add structure")

        self.remove_structure = QtWidgets.QPushButton(self.widget)
        self.remove_structure.setObjectName("remove_structure")
        self.remove_structure.setText("Remove selected")

        self.structure_layout.addWidget(self.Add_structure)
        self.structure_layout.addWidget(self.remove_structure)

        self.structure_widget.setLayout(self.structure_layout)

        self.horizontalLayout_2.addWidget(self.structure_widget)

        self.Structure_list = QtWidgets.QListWidget(self.widget)
        self.Structure_list.setObjectName("Structure_list")
        self.horizontalLayout_2.addWidget(self.Structure_list)

        self.NMR_widget = QtWidgets.QWidget(self)
        self.NMR_layout = QtWidgets.QVBoxLayout(self)

        self.Add_NMR = QtWidgets.QPushButton(self.widget)
        self.Add_NMR.setObjectName("Add_NMR")
        self.Add_NMR.setText("Add NMR")

        self.remove_NMR = QtWidgets.QPushButton(self.widget)
        self.remove_NMR.setObjectName("remove_NMR")
        self.remove_NMR.setText("Remove selected")

        self.NMR_layout.addWidget(self.Add_NMR)
        self.NMR_layout.addWidget(self.remove_NMR)

        self.NMR_widget.setLayout(self.NMR_layout)

        self.horizontalLayout_2.addWidget(self.NMR_widget)

        self.NMR_list = QtWidgets.QListWidget(self.widget)
        self.NMR_list.setObjectName("NMR_list")
        self.horizontalLayout_2.addWidget(self.NMR_list)

        self.Output_add = QtWidgets.QPushButton(self.widget)
        self.Output_add.setObjectName("Out add")
        self.horizontalLayout_2.addWidget(self.Output_add)

        self.Output_list = QtWidgets.QListWidget(self.widget)
        self.Output_list.setObjectName("Out list")
        self.horizontalLayout_2.addWidget(self.Output_list)

        self.widget1 = QtWidgets.QWidget(self)
        self.widget1.setGeometry(QtCore.QRect(10, 160, 710, 51))
        self.widget1.setObjectName("widget1")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget1)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.Gen_diastereomers_yn = QtWidgets.QCheckBox(self.widget1)
        self.Gen_diastereomers_yn.setObjectName("Gen_diastereomers_yn")
        self.horizontalLayout.addWidget(self.Gen_diastereomers_yn)
        self.Solvent_yn = QtWidgets.QCheckBox(self.widget1)
        self.Solvent_yn.setObjectName("Solvent_yn")
        self.horizontalLayout.addWidget(self.Solvent_yn)
        self.MM_yn = QtWidgets.QCheckBox(self.widget1)
        self.MM_yn.setObjectName("MM_yn")
        self.horizontalLayout.addWidget(self.MM_yn)
        self.DFTGeom_yn = QtWidgets.QCheckBox(self.widget1)
        self.DFTGeom_yn.setObjectName("DFTGeom_yn")
        self.horizontalLayout.addWidget(self.DFTGeom_yn)
        self.Energy_yn = QtWidgets.QCheckBox(self.widget1)
        self.Energy_yn.setObjectName("Energy_yn")
        self.horizontalLayout.addWidget(self.Energy_yn)
        self.NMR_calc_yn = QtWidgets.QCheckBox(self.widget1)
        self.NMR_calc_yn.setObjectName("NMR_calc_yn")
        self.horizontalLayout.addWidget(self.NMR_calc_yn)

        self.Assignment_yn = QtWidgets.QCheckBox(self)
        self.Assignment_yn.setGeometry(QtCore.QRect(730, 170, 101, 31))
        self.Assignment_yn.setObjectName("Assignment_yn")
        self.Assignment_yn.setText("NMR\nAssignment")


        self.DP4_stat_yn = QtWidgets.QCheckBox(self)
        self.DP4_stat_yn.setGeometry(QtCore.QRect(730, 240, 101, 31))
        self.DP4_stat_yn.setObjectName("DP4_stat_yn")



        #self.horizontalLayout.addWidget(self.DP4_stat_yn)
        self.label.setText("PyDP4 GUI")
        self.label_2.setText("Workflow")
        self.label_3.setText("Functional")
        self.label_4.setText("Basis set")
        self.label_5.setText("Basis set")
        self.label_6.setText("Functional")
        self.label_7.setText("Basis set")
        self.label_8.setText("Functional")
        self.label_9.setText("Solvent")
        self.label_11.setText("Output")
        self.Gobutton.setText("Calculate")
        self.Add_stats_model.setText("Add stats model")
        self.Solvent_yn.setText("Solvent")
        self.Gen_diastereomers_yn.setText("Generate\n"
                                          "diastereomers")
        self.MM_yn.setText("Molecular\n"
                           "mechanics")
        self.DFTGeom_yn.setText("DFT\n"
                                "Geometry\n"
                                "optimisation")
        self.Energy_yn.setText("Split single\n"
                               "point energy")
        self.NMR_calc_yn.setText("NMR\n"
                                 "calculations")
        self.DP4_stat_yn.setText("DP4 Statistics")

        self.Output_add.setText("Output Folder")

        self.MM_rb = QtWidgets.QRadioButton(self)
        self.MM_rb.setGeometry(QtCore.QRect(250, 240, 101, 31))
        self.MM_rb.setObjectName("MM_rb")
        self.label_12 = QtWidgets.QLabel(self)
        self.label_12.setGeometry(QtCore.QRect(270, 240, 101, 31))
        self.label_12.setText("MacroModel")


        self.Tinker_rb = QtWidgets.QRadioButton(self)
        self.Tinker_rb.setGeometry(QtCore.QRect(250, 300, 101, 31))
        self.Tinker_rb.setObjectName("Tinker_rb")
        self.label_13 = QtWidgets.QLabel(self)
        self.label_13.setGeometry(QtCore.QRect(270, 300, 101, 31))
        self.label_13.setText("Tinker")

        #################################################################################################buttons methods

        # adding structures to the gui

        self.NMR_paths = []

        self.Structure_paths = []

        self.Output_folder = Path.cwd()

        self.Add_structure.clicked.connect(self.addstructure)

        self.remove_structure.clicked.connect(self.removestructure)


        self.Add_NMR.clicked.connect(self.addNMR)

        self.remove_NMR.clicked.connect(self.removeNMR)

        self.Output_add.clicked.connect(self.addoutputfolder)

        # selecting solvent check box

        self.solvent_drop.setEnabled(False)

        self.Solvent_yn.stateChanged.connect(self.solventtoggle)

        self.MM_yn.stateChanged.connect(self.MMtoggle)

        self.MM_rb.toggled.connect(self.rb_toggle)

        self.Tinker_rb.toggled.connect(self.rb_toggle)

        # selecting DFT geometry opt box

        self.DFT_geom_functional_drop.setEnabled(False)

        self.DFT_geom_basis_drop.setEnabled(False)

        self.DFTGeom_yn.stateChanged.connect(self.DFTopttoggle)

        # selecting Split Single point box

        self.Energy_functional_drop.setEnabled(False)

        self.Energy_basis_drop.setEnabled(False)

        self.Energy_yn.stateChanged.connect(self.Energytoggle)

        # selecting NMR box

        self.NMR_functional_drop.setEnabled(False)

        self.NMR_basis_drop.setEnabled(False)

        self.NMR_calc_yn.stateChanged.connect(self.NMRtoggle)

        # add solvents to solvent box

        solvents = ['chloroform', 'dimethylsulfoxide', 'benzene', 'methanol', 'pyridine', 'acetone']

        self.solvent_drop.addItems(solvents)

        # add functionals and basis sets to DFTopt, Energy and NMR

        DFTopt_basis = ['6-31g(d)', '6-311g(d)', 'def2svp', 'def2tzvp']

        DFTopt_functional = ['B3LYP', 'm062x', 'mPW1PW91']

        Energy_basis = ['6-31g(d)', '6-311g(d)', 'def2svp', 'def2tzvp']

        Energy_functional = ['m062x', 'mPW1PW91', 'B3LYP']

        NMR_basis = ['6-311g(d)', '6-31g(d)', 'def2svp', 'def2tzvp']

        NMR_functional = ['mPW1PW91', 'B3LYP', 'M062X']

        self.DFT_geom_functional_drop.addItems(DFTopt_functional)

        self.DFT_geom_basis_drop.addItems(DFTopt_basis)

        self.Energy_functional_drop.addItems(Energy_functional)

        self.Energy_basis_drop.addItems(Energy_basis)

        self.NMR_basis_drop.addItems(NMR_basis)

        self.NMR_functional_drop.addItems(NMR_functional)

        self.Assignment_yn.stateChanged.connect(self.Assignment_toggle)

        # adding a stats model

        self.Add_stats_model.setEnabled(False)

        self.DP4_stat_yn.stateChanged.connect(self.Statstoggle)

        self.Add_stats_model.clicked.connect(self.addstats)

        #####################################################################################running PyDP4 in new thread

        # self.Gobutton.clicked.connect(self.Gotoggle)

        self.Gobutton.clicked.connect(self.get_current_values)

        # make worker object

        self.worker = PyDP4WorkerObject()

        # make thread

        self.thread = QtCore.QThread()

        # move the worker object to the ne thread

        self.worker.moveToThread(self.thread)

        # connect workers finished signal to quit thread

        self.worker.finished.connect(self.thread.quit)

        # connect workers finished signal to enable go button

        self.worker.finished.connect(self.Gotoggle)

        self.worker.finished.connect(self.enabletabs)

        # connect start background signal to background job slot

        self.Gobutton.clicked.connect(self.start_PyDP4)

        # start pydp4 give start signal

        # go button press disables go button

        self.Gobutton.clicked.connect(self.Gotoggle)

        # start signal starts pydp4

        self.signal_start_PyDP4.connect(self.worker.runPyDP4)

        ##############################################################################getting current values of boxs etc

        ###################################################################################

    def enabletabs(self):

        ui.table_widget.addplottabs()

    def addoutputfolder(self):

        # filename = QtWidgets.QFileDialog.getOpenFileName()
        filename = QtWidgets.QFileDialog.getExistingDirectory()

        # self.NMR_list.addItem(str(filename[0].split("/")[-1]))
        self.Output_list.clear()
        self.Output_list.addItem(filename)
        self.Output_folder = Path(filename)

    def get_current_values(self):

        import PyDP4
        
        self.settings = PyDP4.Settings()

        # Read config file and fill in settings in from that
        self.settings = PyDP4.ReadConfig(self.settings)

        #add output folder

        self.settings.OutputFolder = self.Output_folder

        self.settings.InputFilesPaths = self.Structure_paths

        # add structures

        for index in range(self.Structure_list.count()):

            if self.Structure_list.item(index).text() != '':

                self.settings.InputFiles.append(self.Structure_list.item(index).text())

        # copy structures to output folder

        for f in self.Structure_paths:

            if not Path(self.Output_folder / f.name).exists():

                os.path.copy(f,self.settings.OutputFolder)

        # add NMR

        self.settings.NMRsource = self.NMR_paths

        # get workflow information

        # solvent

        if self.Solvent_yn.isChecked() == 1:
            self.settings.Solvent = self.solvent_drop.currentText()

        # generate diastereomers

        self.settings.Workflow = ''

        if self.Gen_diastereomers_yn.isChecked() == 1:
            self.settings.Workflow += 'g'

        # molecular mechanics

        if self.MM_yn.isChecked() == 1:

            self.settings.Workflow += 'm'

            if self.MM_rb.isChecked() == True:

                self.settings.MM = 'm'

            else:
                
                self.settings.MM = 't'

        # DFT Geometry optimisation

        if self.DFTGeom_yn.isChecked() == 1:
            self.settings.Workflow += 'o'
            self.settings.oBasisSet = self.DFT_geom_basis_drop.currentText()
            self.settings.oFunctional = self.DFT_geom_functional_drop.currentText()

        # Split single point

        if self.Energy_yn.isChecked() == 1:
            self.settings.Workflow += 'e'
            self.settings.eBasisSet = self.Energy_basis_drop.currentText()
            self.settings.eFunctional = self.Energy_functional_drop.currentText()

        # NMR

        # Split single point

        if self.NMR_calc_yn.isChecked() == 1:
            self.settings.Workflow += 'n'
            self.settings.nBasisSet = self.NMR_basis_drop.currentText()
            self.settings.nFunctional = self.NMR_functional_drop.currentText()

        if self.DP4_stat_yn.isChecked():

            self.settings.Workflow += 's'

            if self.Stats_list.item(0) != None:
                self.settings.StatsParamFile = self.Stats_list.item(0).text()
                self.settings.StatsModel = 'm'
                
        elif self.Assignment_yn.isChecked():
            
            self.settings.Workflow += 'a'

        self.settings.ScriptDir = os.path.dirname(os.path.realpath(sys.argv[0]))

    def start_PyDP4(self):

        # No harm in calling thread.start() after the thread is already started.

        # start the thread

        self.thread.start()

        self.thread.finished.connect(self.Gotoggle)

        # send background job start signal

        self.signal_start_PyDP4.emit()

        self.thread.disconnect()

    def addstructure(self):

        f = QtWidgets.QFileDialog.getOpenFileName()[0]

        if f:

            filename = Path(f)

            self.Structure_list.addItem(filename.name)
            self.Structure_paths.append(filename)

    def removestructure(self):

        item = self.Structure_list.selectedItems()
        if not item:
            return
        for i in item:
            self.Structure_list.takeItem(self.Structure_list.row(i))
            self.Structure_paths.pop(self.Structure_list.row(i))

    def addNMR(self):
        
        # filename = QtWidgets.QFileDialog.getOpenFileName()

        i = QtWidgets.QFileDialog.getExistingDirectory()

        if i:

            filename = Path(i)

            p_switch = 0

            c_switch = 0

            for f in filename.iterdir():

                if f.name == "Carbon" or f.name == "carbon" or f.name == "Carbon.dx" or f.name == "carbon.dx":
                    self.NMR_list.addItem(f.name)
                    self.NMR_paths.append(f)
                    c_switch = 1

                elif f.name == "Proton" or f.name== "proton" or f.name == "Proton.dx" or f.name== "proton.dx":
                    self.NMR_list.addItem(f.name)
                    self.NMR_paths.append(f)
                    p_switch = 1

                if p_switch == 1 and c_switch == 1:
                    break

            # self.NMR_list.addItem(str(filename[0].split("/")[-1]))

            if p_switch == 0 and c_switch == 0:
                self.NMR_list.addItem(filename.name)
                self.NMR_paths.append(f)

    def removeNMR(self):

        item = self.NMR_list.selectedItems()
        if not item:
            return
        for i in item:
            self.NMR_list.takeItem(self.NMR_list.row(i))
            self.NMR_paths.pop(self.NMR_list.row(i))

    def addstats(self):
        filename = QtWidgets.QFileDialog.getOpenFileName()
        self.Stats_list.addItem(str(filename[0]))

    def solventtoggle(self, state):

        if state > 0:
            self.solvent_drop.setEnabled(True)
            self.Gen_diastereomers_yn.setChecked(True)

        else:
            self.solvent_drop.setEnabled(False)
            self.MM_yn.setChecked(False)

    def MMtoggle(self, state):

        if state > 0:

            self.Gen_diastereomers_yn.setChecked(True)

            self.Solvent_yn.setChecked(True)
            self.solvent_drop.setEnabled(True)


            if (self.MM_rb.isDown() == False) & (self.Tinker_rb.isDown() == False):
                self.MM_rb.toggle()

        else:
            self.solvent_drop.setEnabled(False)
            self.Solvent_yn.setChecked(False)
            self.MM_rb.setChecked(False)
            self.Tinker_rb.setChecked(False)

    def rb_toggle(self,state):

        if state > 0:

            if state > 0:

                self.MM_yn.setChecked(True)
                self.Gen_diastereomers_yn.setChecked(True)
                self.Solvent_yn.setChecked(True)
                self.solvent_drop.setEnabled(True)


            else:
                self.solvent_drop.setEnabled(False)

    def Energytoggle(self, state):

        if state > 0:
            self.Energy_functional_drop.setEnabled(True)
            self.Energy_basis_drop.setEnabled(True)
            self.Solvent_yn.setChecked(True)
            self.solvent_drop.setEnabled(True)
            self.Gen_diastereomers_yn.setChecked(True)
            self.MM_yn.setChecked(True)

        else:
            self.Energy_functional_drop.setEnabled(False)
            self.Energy_basis_drop.setEnabled(False)

    def DFTopttoggle(self, state):

        if state > 0:
            self.DFT_geom_functional_drop.setEnabled(True)
            self.DFT_geom_basis_drop.setEnabled(True)

            self.Solvent_yn.setChecked(True)
            self.solvent_drop.setEnabled(True)
            self.Gen_diastereomers_yn.setChecked(True)
            self.MM_yn.setChecked(True)

        else:
            self.DFT_geom_functional_drop.setEnabled(False)
            self.DFT_geom_basis_drop.setEnabled(False)

    def NMRtoggle(self, state):

        if state > 0:
            self.NMR_functional_drop.setEnabled(True)
            self.NMR_basis_drop.setEnabled(True)
            self.Solvent_yn.setChecked(True)
            self.solvent_drop.setEnabled(True)
            self.Gen_diastereomers_yn.setChecked(True)
            self.MM_yn.setChecked(True)

        else:
            self.NMR_functional_drop.setEnabled(False)
            self.NMR_basis_drop.setEnabled(False)

    def Assignment_toggle(self,state):

        if state > 0:

            self.NMR_calc_yn.setChecked(True)
            self.NMR_functional_drop.setEnabled(True)
            self.NMR_basis_drop.setEnabled(True)
            self.Solvent_yn.setChecked(True)
            self.solvent_drop.setEnabled(True)
            self.Gen_diastereomers_yn.setChecked(True)
            self.MM_yn.setChecked(True)

        else:
            self.DP4_stat_yn.setChecked(False)
            self.Add_stats_model.setEnabled(False)

    def Statstoggle(self, state):

        if state > 0:
            self.Add_stats_model.setEnabled(True)
            self.NMR_calc_yn.setChecked(True)
            self.NMR_functional_drop.setEnabled(True)
            self.NMR_basis_drop.setEnabled(True)
            self.Solvent_yn.setChecked(True)
            self.solvent_drop.setEnabled(True)
            self.Gen_diastereomers_yn.setChecked(True)
            self.MM_yn.setChecked(True)
            self.Assignment_yn.setChecked(True)

        else:
            self.Add_stats_model.setEnabled(False)

    def append_text(self, text):
        self.Output_box.moveCursor(QtGui.QTextCursor.End)
        self.Output_box.insertPlainText(text)
        #self.log_file.write(text)

        self.worker.log_file.write(text)

    def Gotoggle(self):

        if self.Gobutton.isEnabled() == True:

            self.Gobutton.setEnabled(False)

        else:

            self.Gobutton.setEnabled(True)


class ProtonPlotTab(QtWidgets.QWidget):

    def __init__(self):

        super(ProtonPlotTab, self).__init__()

        self.cwd = Path(os.getcwd())

        # create a figure instance

        self.figure = Figure()

        # create the canvas widget thats displays figure

        self.canvas = FigureCanvas(self.figure)

        # make the navigation widget - this takes the canvas widget as the parent

        self.toolbar = NavigationToolbar(self.canvas, self)

        self.IsomerSelect = QtWidgets.QComboBox(self)

        self.IsomerSelect.addItems(self.Isomer_number())

        self.IsomerSelect.currentIndexChanged.connect(self.PlotProton)
        self.image = QSvgWidget()

        self.widget1 = QtWidgets.QWidget(self)

        self.widget2 = QtWidgets.QWidget(self)

        self.hl1 = QtWidgets.QVBoxLayout(self.widget1)

        self.hl2 = QtWidgets.QVBoxLayout(self.widget2)

        self.hl1.addWidget(self.toolbar)

        self.hl1.addWidget(self.canvas)

        self.hl2.addWidget(self.IsomerSelect)

        self.hl2.addWidget(self.image)

        self.widget1.setGeometry(QtCore.QRect(300, 0, 1200, 875))

        # self.IsomerSelect.setGeometry(QtCore.QRect(0,0,100,50))

        # self.image.setGeometry(QtCore.QRect(0,50,300,300))

        self.widget2.setGeometry(QtCore.QRect(0, 0, 300, 400))

        self.canvas.mpl_connect('button_press_event', self.selectpoint)

        ################################################################################################################

        if ui.table_widget.Tab1.settings.OutputFolder == '':

            pdir = self.cwd  /  "Pickles"

        else:
            pdir =  ui.table_widget.Tab1.settings.OutputFolder /  "Pickles"


        if os.path.isfile(pdir / ui.table_widget.Tab1.settings.InputFiles[0] /  "protondata"):

            self.protondata = pickle.load( Path(pdir / ui.table_widget.Tab1.settings.InputFiles[0] / "protondata").open(mode = "rb"))

        self.xdata = self.protondata["xdata"]

        self.ydata = self.protondata["ydata"]

        self.centres = self.protondata["centres"]

        self.exp_peaks = self.protondata["exppeaks"]

        self.peak_regions = self.protondata["peakregions"]

        self.cummulative_vectors = self.protondata["cummulativevectors"]

        self.integral_sum = self.protondata["integralsum"]

        self.integrals = self.protondata["integrals"]

        self.sim_regions = self.protondata["sim_regions"]

        self.PlotProton()

        ################################################################################################################

    def Isomer_number(self):

        Isomer_list = []

        for c, i in enumerate(ui.table_widget.Tab1.worker.Isomers):
            Isomer_list.append("Isomer " + str(c +1))

        return Isomer_list

    def PlotProton(self):

        self.RenderImage([], None)

        self.isomerindex = int(str(self.IsomerSelect.currentText())[-1])

        self.isomer = ui.table_widget.Tab1.worker.Isomers[self.isomerindex]

        self.assigned_shifts = self.isomer.Hshifts

        self.assigned_peaks = []

        for peak in self.isomer.Hexp:

            if peak != '':
                self.assigned_peaks.append(peak)

        self.assigned_labels = self.isomer.Hlabels

        # check if pickle and DP4output files are in place

        if ui.table_widget.Tab1.worker.settings.OutputFolder == '':

            pdir = Path.cwd() / "Pickles"

        else:

            pdir = ui.table_widget.Tab1.worker.settings.OutputFolder / "Pickles"

        if Path(pdir / ui.table_widget.Tab1.worker.settings.InputFiles[0] / "protondata").exists():

            self.figure.clear()

            fig = self.figure.add_subplot(111)

            self.figure.subplots_adjust(left=0.05, right=0.95, bottom=0.07, top=0.95, wspace=0.05, hspace=0.05)

            #################################### will probs need to fix sorting here

            fig.set_xlim([10, 0])

            fig.set_xlabel("ppm")

            fig.plot(self.xdata, self.ydata, label='data', color='grey')

            set_exp = sorted(list(set(self.exp_peaks)))[::-1]

            # simulate_spectrum(xdata, assigned_shifts, assigned_peaks, set_exp)

            ##############################

            for ind, shift in enumerate(self.assigned_shifts):
                exp_p = self.assigned_peaks[ind]

                ind2 = set_exp.index(exp_p)
                y = lorentzian(self.xdata, 0.001, shift, 0.2)

                fig.plot(self.xdata, y + 1.05, color='C' + str(ind2 % 10))

            ##############################

            fig.axhline(1.05, color='grey')

            # plt integral information

            prev = 15

            count = 0

            for index in range(0, len(self.peak_regions)):

                if abs(prev - self.xdata[self.centres[index]]) < 0.45:
                    count += 1
                else:
                    count = 0
                    prev = self.xdata[self.centres[index]]

                fig.annotate(str(self.integrals[index]) + ' Hs',
                             xy=(self.xdata[self.centres[index]], -(0.1) - 0.1 * count), color='C' + str(index % 10))

                fig.annotate(str(round(self.xdata[self.centres[index]], 3)) + ' ppm',
                             xy=(self.xdata[self.centres[index]], -(0.15) - 0.1 * count), color='C' + str(index % 10))

                fig.plot(self.xdata[self.peak_regions[index]],
                         self.cummulative_vectors[index] + self.integral_sum[index],
                         color='C' + str(index % 10),
                         linewidth=2)

            for index in range(0, len(self.peak_regions) - 1):
                fig.plot([self.xdata[self.peak_regions[index][-1]], self.xdata[self.peak_regions[index + 1][0]]],
                         [self.integral_sum[index + 1], self.integral_sum[index + 1]], color='grey')

            for index, region in enumerate(self.peak_regions):
                fig.plot(self.xdata[region], self.sim_regions[index], color='C' + str(index % 10))

            # plt.legend()

            ### plotting assignment

            fig.set_yticks([], [])

            # fig.set_title(str(ui.table_widget.Tab1.settings.InputFiles[0]) +
            #             "\nProton NMR of Isomer " + str(isomerindex + 1) + "\n Number of Peaks Found = " + str(
            #  len(exp_peaks)))

            # plot assignments

            for ind1, peak in enumerate(self.assigned_peaks):
                fig.plot([peak, self.assigned_shifts[ind1]],
                         [1, 1.05], linewidth=0.5, color='cyan')

            # annotate peak locations

            for x, txt in enumerate(self.exp_peaks):

                if self.exp_peaks[x] in self.assigned_peaks:

                    color = 'C1'

                else:

                    color = 'grey'

                fig.plot(txt, -0.02, 'o', color=color)

            # annotate shift positions

            prev = 0

            count = 0

            s = np.argsort(np.array(self.assigned_shifts))

            s_assigned_shifts = np.array(self.assigned_shifts)[s]

            s_assigned_labels = np.array(self.assigned_labels)[s]

            s_assigned_peaks = np.array(self.assigned_peaks)[s]

            for x, txt in enumerate(s_assigned_labels[::-1]):

                w = np.where(set_exp == s_assigned_peaks[::-1][x])[0][0]

                color = w % 10

                if abs(prev - s_assigned_shifts[::-1][x]) < 0.2:
                    count += 1

                else:
                    count = 0
                    prev = s_assigned_shifts[::-1][x]

                fig.annotate(txt, (s_assigned_shifts[::-1][x], + 1.25 + 0.05 * count), color='C' + str(color))

            # ax1.plot(picked_peaks_ppm,ydata[picked_peaks],
            #        'co', label='Picked Peaks')

            fig.set_ylim([-0.5, 2.0])

            self.canvas.draw()

        else:
            pass

    def selectpoint(self, event):

        if event.dblclick:

            self.xpos = event.xdata

            self.ypos = event.ydata

            # find the cloest point to the click


            if self.xpos is None and self.xpos is None:

                self.PlotProton()

            elif self.ypos < 1:

                mindis = np.argmin(abs(self.xdata[self.centres] - self.xpos))

                self.PlotProtonSelected(mindis)

                # find which protons this peak has been assigned to

                p = np.where([round(i,4) for i in self.assigned_peaks] == round(self.xdata[self.centres[mindis]],4))[0]

                la = [int(self.assigned_labels[j][1:]) - 1  for j in p]


                self.RenderImage(la, mindis)

            else:

                # find closest assigned shift

                m = np.argmin(abs(np.array(self.assigned_shifts) - self.xpos))

                # find which peak this is assigned to

                p = self.assigned_peaks[m]

                mindis = np.argmin(abs(p - self.xdata[self.centres]))

                p = np.where(self.assigned_peaks == round(self.xdata[self.centres[mindis]], 4))[0]

                la = [int(self.assigned_labels[j][1:]) - 1 for j in p]

                self.PlotProtonSelected(mindis)

                self.RenderImage(la, mindis)

    def PlotProtonSelected(self, mindis):

        # check if pickle and DP4output files are in place

        if ui.table_widget.Tab1.worker.settings.OutputFolder == '':

            pdir = Path.cwd() / "Pickles"

        else:

            pdir = ui.table_widget.Tab1.worker.settings.OutputFolder / "Pickles"

        if Path(pdir / ui.table_widget.Tab1.worker.settings.InputFiles[0] / "protondata").exists():

            self.figure.clear()

            fig = self.figure.add_subplot(111)

            self.figure.subplots_adjust(left=0.05, right=0.95, bottom=0.07, top=0.95, wspace=0.05, hspace=0.05)

            assigned_shifts = self.isomer.Hshifts

            assigned_peaks = []

            for peak in self.isomer.Hexp:

                if peak != '':
                    assigned_peaks.append(peak)

            assigned_labels = self.isomer.Hlabels

            #################################### will probs need to fix sorting here

            fig.set_xlim([10, 0])

            fig.set_xlabel("ppm")

            fig.plot(self.xdata, self.ydata, label='data', color='grey', alpha=0.5)

            set_exp = sorted(list(set(self.exp_peaks)))[::-1]

            # simulate_spectrum(xdata, assigned_shifts, assigned_peaks, set_exp)

            ##############################

            for ind, shift in enumerate(assigned_shifts):

                exp_p = assigned_peaks[ind]

                ind2 = set_exp.index(exp_p)

                y = lorentzian(self.xdata, 0.001, shift, 0.2)

                if ind2 == mindis:

                    fig.plot(self.xdata, y + 1.05, color='C' + str(ind2 % 10))

                else:

                    fig.plot(self.xdata, y + 1.05, color='grey', alpha=0.5)

            ##############################

            fig.axhline(1.05, color='grey')

            # plt integral information

            prev = 15

            count = 0

            for index, region in enumerate(self.peak_regions):
                fig.plot(self.xdata[region], self.sim_regions[index], color='grey')

            fig.plot(self.xdata[self.peak_regions[mindis]], self.sim_regions[mindis], color='C' + str(mindis))

            fig.annotate(str(self.integrals[mindis]) + ' Hs',
                         xy=(self.xdata[self.centres[mindis]], -(0.1) - 0.1 * count), color='C' + str(mindis))

            fig.annotate(str(round(self.xdata[self.centres[mindis]], 3)) + ' ppm',
                         xy=(self.xdata[self.centres[mindis]], -(0.15) - 0.1 * count), color='C' + str(mindis))

            fig.plot(self.xdata[self.peak_regions[mindis]],
                     self.cummulative_vectors[mindis] + self.integral_sum[mindis],
                     color='C' + str(mindis % 10),
                     linewidth=2)
            # plt.legend()

            ### plotting assignment

            fig.set_yticks([], [])

            # fig.set_title(str(ui.table_widget.Tab1.settings.InputFiles[0]) +
            #             "\nProton NMR of Isomer " + str(isomerindex + 1) + "\n Number of Peaks Found = " + str(
            #  len(exp_peaks)))

            # plot assignments

            # annotate shift positions

            prev = 0

            count = 0

            s = np.argsort(np.array(assigned_shifts))

            s_assigned_shifts = np.array(assigned_shifts)[s]

            s_assigned_labels = np.array(assigned_labels)[s]

            s_assigned_peaks = np.array(assigned_peaks)[s]

            for x, txt in enumerate(s_assigned_labels[::-1]):

                w = np.where(set_exp == s_assigned_peaks[::-1][x])[0][0]

                if w == mindis:

                    color = w % 10

                    if abs(prev - s_assigned_shifts[::-1][x]) < 0.2:
                        count += 1

                    else:
                        count = 0
                        prev = s_assigned_shifts[::-1][x]

                    fig.annotate(txt, (s_assigned_shifts[::-1][x], + 1.25 + 0.05 * count), color='C' + str(color))

            # ax1.plot(picked_peaks_ppm,ydata[picked_peaks],
            #        'co', label='Picked Peaks')

            fig.set_ylim([-0.5, 2.0])

            for x, txt in enumerate(self.exp_peaks):

                if self.exp_peaks[x] in self.assigned_peaks:

                    color = 'C1'

                else:

                    color = 'grey'

                fig.plot(txt, -0.02, 'o', color=color)

            self.canvas.draw()

        else:
            pass

    def RenderImage(self, atom, color):

        colors = [(0.12, 0.47, 0.71), (1.0, 0.5, 0.05), (0.17, 0.63, 0.17), (0.84, 0.15, 0.16), (0.58, 0.4, 0.74),
                  (0.55, 0.34, 0.29), (0.89, 0.47, 0.76), (0.5, 0.5, 0.5), (0.74, 0.74, 0.13), (0.09, 0.75, 0.81)]

        highlight = {}

        for i in atom:
            highlight[i] = colors[color % 10]

        #m = Chem.MolFromMolFile(str(ui.table_widget.Tab1.worker.settings.InputFiles[0]).split('.sdf')[0] + '.sdf', removeHs=False)

        m = Chem.MolFromMolFile(str(ui.table_widget.Tab1.worker.settings.InputFilesPaths[0]), removeHs=False)

        Chem.Compute2DCoords(m)

        drawer = rdMolDraw2D.MolDraw2DSVG(300, 300)

        drawer.DrawMolecule(m, highlightAtoms=atom, highlightAtomColors=highlight)

        drawer.FinishDrawing()

        svg = drawer.GetDrawingText().replace('svg:', '')

        svg_bytes = bytearray(svg, encoding='utf-8')

        self.image.renderer().load(svg_bytes)

        self.image.setGeometry(QtCore.QRect(0, 50, 300, 300))


        ui.update()

        # f = open("f.svg", "w+")

        # f.write(str(svg))


class CarbonPlotTab(QtWidgets.QWidget):

    def __init__(self):

        super(CarbonPlotTab, self).__init__()

        # create a figure instance

        self.figure = Figure()

        # create the canvas widget thats displays figure

        self.canvas = FigureCanvas(self.figure)

        # make the navigation widget - this takes the canvas widget as the parent

        self.toolbar = NavigationToolbar(self.canvas, self)

        self.IsomerSelect = QtWidgets.QComboBox(self)

        self.IsomerSelect.addItems(self.Isomer_number())

        self.IsomerSelect.currentIndexChanged.connect(self.PlotCarbon)

        self.image = QSvgWidget()

        self.widget1 = QtWidgets.QWidget(self)

        self.widget2 = QtWidgets.QWidget(self)

        self.hl1 = QtWidgets.QVBoxLayout(self.widget1)

        self.hl2 = QtWidgets.QVBoxLayout(self.widget2)

        self.hl1.addWidget(self.toolbar)

        self.hl1.addWidget(self.canvas)

        self.hl2.addWidget(self.IsomerSelect)

        self.hl2.addWidget(self.image)

        self.widget1.setGeometry(QtCore.QRect(300, 0, 1200, 875))

        self.widget2.setGeometry(QtCore.QRect(0, 0, 300, 400))

        self.canvas.mpl_connect('button_press_event', self.selectpoint)

        #############################

        if ui.table_widget.Tab1.settings.OutputFolder == '':

            pdir = Path.cwd() /  "Pickles"

        else:
            pdir =  ui.table_widget.Tab1.settings.OutputFolder /  "Pickles"


        if Path(pdir / ui.table_widget.Tab1.settings.InputFiles[0] /  "carbondata").exists():

            self.carbondata = pickle.load(Path(pdir / ui.table_widget.Tab1.settings.InputFiles[0] / "carbondata").open(mode= "rb"))

        self.xdata = self.carbondata["xdata"]

        self.ydata = self.carbondata["ydata"]

        self.exppeaks = self.carbondata["exppeaks"]

        self.simulated_ydata = self.carbondata["simulated_ydata"]

        self.removed = self.carbondata["removed"]

        self.PlotCarbon()

        #############################

    def Isomer_number(self):

        Isomer_list = []

        for c, i in enumerate(ui.table_widget.Tab1.worker.Isomers):
            Isomer_list.append("Isomer " + str(c+ 1))

        return Isomer_list

    def PlotCarbon(self):

        self.RenderImage([])

        if ui.table_widget.Tab1.worker.settings.OutputFolder == '':

            pdir = Path.cwd() / "Pickles"

        else:

            pdir = ui.table_widget.Tab1.worker.settings.OutputFolder / "Pickles"

        if Path(pdir / ui.table_widget.Tab1.worker.settings.InputFiles[0] / "carbondata").exists():

            self.figure.clear()

            fig = self.figure.add_subplot(111)

            self.figure.subplots_adjust(left=0.05, right=0.95, bottom=0.07, top=0.95, wspace=0.05, hspace=0.05)

            self.isomerindex = int(str(self.IsomerSelect.currentText())[-1])

            self.isomer = ui.table_widget.Tab1.worker.Isomers[self.isomerindex]
            self.assigned_shifts = self.isomer.Cshifts

            self.assigned_peaks = []

            for peak in self.isomer.Cexp:

                if peak != '':
                    self.assigned_peaks.append(peak)

            self.assigned_labels = self.isomer.Clabels

            ###################will probs need to fix sorting here

            exppeaks_ppm = self.xdata[self.exppeaks].tolist()

            shiftlist = self.assigned_shifts

            totallist = exppeaks_ppm + shiftlist

            fig.set_xlim([max(totallist) + 10, min(totallist) - 10])

            fig.plot(self.xdata, self.ydata, color='grey', linewidth=0.75, label='experimental spectrum')
            fig.plot(self.xdata, self.simulated_ydata, label='simulated spectrum')

            fig.set_xlabel('PPM')  # axis labels

            # plt.yticks([], [])
            # fig.set_title(str(ui.table_widget.Tab1.worker.settings.InputFiles[0]) +
            #             "\nCarbon NMR of Isomer " + str(self.isomerindex + 1) + "\n Number of Peaks Found = " + str(
            #  len(self.exppeaks)))

            # plot assignments

            for ind1, peak in enumerate(self.assigned_peaks):
                wh = np.argmin(abs(self.xdata - peak))

                fig.plot([peak, self.assigned_shifts[ind1]],
                         [self.ydata[wh], 1.1], linewidth=0.5, color='cyan')

            prev = round(exppeaks_ppm[0], 2)

            count = 0

            # annotate peak locations

            for x, txt in enumerate([round(i, 2) for i in exppeaks_ppm]):

                if abs(prev - txt) < 5:

                    count += 1
                else:
                    count = 0
                    prev = txt

                if exppeaks_ppm[x] in self.assigned_peaks:
                    color = 'C1'
                else:
                    color = 'grey'

                fig.annotate(txt, (exppeaks_ppm[x], -0.06 - 0.025 * count), color=color)

                fig.plot(exppeaks_ppm[x], self.ydata[self.exppeaks[x]], 'o', color=color)

            if len(self.removed) > 0:
                fig.plot(self.xdata[self.removed],
                         self.simulated_ydata[self.removed], "ro")

            # annotate shift positions

            count = 0

            ####some quick sorting

            argss = np.argsort(self.assigned_shifts)
            sortshifts = np.sort(self.assigned_shifts)[::-1]
            slabels = np.array(self.assigned_labels)[argss][::-1]

            prev = sortshifts[0]

            for x, txt in enumerate(slabels):

                if abs(prev - sortshifts[x]) < 4:
                    count += 1
                else:
                    count = 0
                    prev = sortshifts[x]

                fig.annotate(txt, (sortshifts[x], + 2.05 + 0.05 * count))

            ##########

            simulated_calc_ydata = np.zeros(len(self.xdata))

            for peak in self.assigned_shifts:
                y = np.exp(-0.5 * ((self.xdata - peak) / 0.002) ** 2)
                simulated_calc_ydata += y

            scaling_factor = np.amax(self.simulated_ydata) / np.amax(simulated_calc_ydata)

            simulated_calc_ydata = simulated_calc_ydata * scaling_factor

            #########

            fig.plot(self.xdata, simulated_calc_ydata + 1.1, label='calculated spectrum')

            self.canvas.draw()

    def selectpoint(self, event):

        if event.dblclick:

            self.xpos = event.xdata

            self.ypos = event.ydata

            # find the cloest point to the click

            if self.xpos is None and self.xpos is None:

                self.PlotCarbon()

            elif self.ypos < 1:

                mindis = np.argmin(abs(self.xdata[self.exppeaks] - self.xpos))

                self.PlotCarbonSelected(mindis)

                # find which protons this peak has been assigned to



                p = np.where(self.assigned_peaks == self.xdata[self.exppeaks[mindis]])[0]

                la = [int(self.assigned_labels[j][1:]) - 1 for j in p]

                self.RenderImage(la)

            else:

                # find closest assigned shift

                m = np.argmin(abs(np.array(self.assigned_shifts) - self.xpos))

                # find which peak this is assigned to

                p = self.assigned_peaks[m]

                mindis = np.argmin(abs(p - self.xdata[self.exppeaks]))

                p = np.where(self.assigned_peaks == self.xdata[self.exppeaks[mindis]])[0]

                la = [int(self.assigned_labels[j][1:]) - 1 for j in p]

                self.PlotCarbonSelected(mindis)

                self.RenderImage(la)

    def PlotCarbonSelected(self, mindis):

        if ui.table_widget.Tab1.worker.settings.OutputFolder == '':

            pdir = Path.cwd() / "Pickles"

        else:

            pdir = ui.table_widget.Tab1.worker.settings.OutputFolder / "Pickles"

        if Path(pdir / ui.table_widget.Tab1.worker.settings.InputFiles[0] / "carbondata").exists():

            self.figure.clear()

            fig = self.figure.add_subplot(111)

            self.figure.subplots_adjust(left=0.05, right=0.95, bottom=0.07, top=0.95, wspace=0.05, hspace=0.05)

            exppeaks_ppm = self.xdata[self.exppeaks].tolist()

            shiftlist = self.assigned_shifts

            totallist = exppeaks_ppm + shiftlist

            fig.set_xlim([max(totallist) + 10, min(totallist) - 10])

            fig.plot(self.xdata, self.ydata, color='grey', linewidth=0.75, label='experimental spectrum')

            fig.plot(self.xdata, self.simulated_ydata, label='simulated spectrum')

            fig.set_xlabel('PPM')  # axis labels

            assigned_peak = exppeaks_ppm[mindis]


            s = np.where(np.round(self.assigned_peaks, 8) == np.round(assigned_peak, 8))[0]


            assigned_shift = np.array(self.assigned_shifts)[s]


            assigned_label = np.array(self.assigned_labels)[s]

            for i in assigned_shift:


                fig.plot([assigned_peak, i], [self.ydata[self.exppeaks[mindis]], 1.1], color='cyan')

            # plot assignments

            # for ind1, peak in enumerate(self.assigned_peaks):
            #   wh = np.argmin(abs(self.xdata - peak))

            #  fig.plot([peak, self.assigned_shifts[ind1]],
            #          [self.ydata[wh], 1.1], linewidth=0.5, color='cyan')

            prev = round(exppeaks_ppm[0], 2)

            count = 0

            # annotate peak locations

            for x, txt in enumerate([round(i, 2) for i in exppeaks_ppm]):

                if exppeaks_ppm[x] == assigned_peak:

                    color = 'cyan'

                elif exppeaks_ppm[x] in self.assigned_peaks:

                    color = 'C1'

                else:
                    color = 'grey'

                fig.plot(exppeaks_ppm[x], self.ydata[self.exppeaks[x]], 'o', color=color)

            fig.annotate(str(round(assigned_peak, 2)), (assigned_peak, -0.06), color='cyan')

            if len(self.removed) > 0:
                fig.plot(self.xdata[self.removed],
                         self.simulated_ydata[self.removed], "ro")

            for l, s in zip(assigned_label, assigned_shift):
                fig.annotate(l, (s, 2.05), color="cyan")

            ##########

            simulated_calc_ydata = np.zeros(len(self.xdata))

            for peak in self.assigned_shifts:
                y = np.exp(-0.5 * ((self.xdata - peak) / 0.002) ** 2)

                simulated_calc_ydata += y

            scaling_factor = np.amax(self.simulated_ydata) / np.amax(simulated_calc_ydata)

            for peak in self.assigned_shifts:
                y = np.exp(-0.5 * ((self.xdata - peak) / 0.002) ** 2)

                fig.plot(self.xdata, y * scaling_factor + 1.1, label='calculated spectrum', color='grey', alpha=0.5)

            for peak in assigned_shift:
                y = np.exp(-0.5 * ((self.xdata - peak) / 0.002) ** 2)

                fig.plot(self.xdata, y * scaling_factor + 1.1, label='calculated spectrum', color='C1')

            #########

            self.canvas.draw()

    def RenderImage(self, atom):

        # colors = [(0.12, 0.47, 0.71), (1.0, 0.5, 0.05), (0.17, 0.63, 0.17), (0.84, 0.15, 0.16), (0.58, 0.4, 0.74), (0.55, 0.34, 0.29), (0.89, 0.47, 0.76), (0.5, 0.5, 0.5), (0.74, 0.74, 0.13), (0.09, 0.75, 0.81)]

        highlight = {}

        for i in atom:
            highlight[i] = (0, 1, 1)

        #m = Chem.MolFromMolFile(str(ui.table_widget.Tab1.worker.settings.InputFiles[0]).split('.sdf')[0] + '.sdf', removeHs=False)
        m = Chem.MolFromMolFile(str(ui.table_widget.Tab1.worker.settings.InputFilesPaths[0]), removeHs=False)
        #m = Chem.MolFromMolFile(ui.table_widget.Tab1.worker.settings.InputFilesPaths[0], removeHs=False)

        # m = Chem.AddHs(m)

        Chem.Compute2DCoords(m)

        drawer = rdMolDraw2D.MolDraw2DSVG(300, 300)

        drawer.DrawMolecule(m, highlightAtoms=atom, highlightAtomColors=highlight)

        drawer.FinishDrawing()

        svg = drawer.GetDrawingText().replace('svg:', '')

        svg_bytes = bytearray(svg, encoding='utf-8')

        self.image.renderer().load(svg_bytes)

        self.image.setGeometry(QtCore.QRect(0, 50, 300, 300))

        ui.update()

        # f = open("f.svg", "w+")

        # f.write(str(svg))


class ConformerTab(QtWidgets.QWidget):
    def __init__(self):

        super(ConformerTab, self).__init__()

        self.layout = QtWidgets.QGridLayout()

        self.setLayout(self.layout)

        self.IsomerSelect = QtWidgets.QComboBox(self)

        self.Isomers = ui.table_widget.Tab1.worker.Isomers

        self.IsomerSelect.addItems(self.Isomer_number())

        self.conformertable = QtWidgets.QTableWidget(self)

        self.layout.addWidget(self.conformertable, 0, 0)

        # self.errortable.setGeometry(QtCore.QRect(10, 50,400, 400))

        self.conformertable.setColumnCount(3)

        self.conformertable.setHorizontalHeaderLabels(["Conformer", "Energy", "Population"])

        self.IsomerSelect.currentIndexChanged.connect(self.populate_table)

        self.layout.setContentsMargins(0, 50, 0, 0)

        self.conffigure = Figure()

        self.confcanvas = FigureCanvas(self.conffigure)

        self.conformertable.itemSelectionChanged.connect(self.plot_conformers)

        self.layout.addWidget(self.confcanvas, 0, 1)

        self.confcanvas.mpl_connect('button_press_event', self.selectpoint)

    def selectpoint(self, event):

        self.xpos = event.xdata

        self.ypos = event.ydata

        # find the cloest point to the click

        coords = self.conffig.transData.transform((self.xpos, self.ypos))

        coordinates = np.array(self.conffig.transData.transform(list(zip(self.energies, self.populations))))

        mindis = np.argmin((coordinates[:, 0] - coords[0]) ** 2 + (coordinates[:, 1] - coords[1]) ** 2)

        self.conformertable.selectRow(mindis)

    def Isomer_number(self):

        Isomer_list = []

        for c, i in enumerate(self.Isomers):
            Isomer_list.append("Isomer " + str(c + 1))

        return Isomer_list

    def populate_table(self):

        c = 0

        self.isomerindex = int(str(self.IsomerSelect.currentText())[-1]) - 1

        self.conformertable.setRowCount(0)

        self.conformertable.setRowCount(len(self.Isomers[self.isomerindex].Energies))

        for energy, population in zip(self.Isomers[self.isomerindex].Energies,
                                      self.Isomers[self.isomerindex].Populations):
            self.conformertable.setItem(c, 0, QtWidgets.QTableWidgetItem(str(c)))

            self.conformertable.setItem(c, 1, QtWidgets.QTableWidgetItem(str(energy)))

            self.conformertable.setItem(c, 2, QtWidgets.QTableWidgetItem(str(population)))

            c += 1

        self.conformertable.selectRow(0)

        self.plot_conformers()

    def plot_conformers(self):

        self.conffigure.clear()

        self.conffig = self.conffigure.add_subplot(111)

        self.isomerindex = int(str(self.IsomerSelect.currentText())[-1]) - 1

        self.energies = np.array(self.Isomers[self.isomerindex].Energies)

        self.populations = np.array(self.Isomers[self.isomerindex].Populations)

        s = np.argsort(self.energies)

        self.conffig.plot(self.energies[s], self.populations[s])

        self.conffig.plot(self.energies, self.populations, 'o', color='C1', alpha=0.5)

        self.conffig.set_xlabel("Energy (Kcal)")

        self.conffig.set_ylabel("Population")

        selected_conformer = int(self.conformertable.currentRow())

        E = self.energies[selected_conformer]

        P = self.populations[selected_conformer]

        self.conffig.plot(E, P, 'o', color='red', alpha=0.75)

        self.conffig.plot([0, E], [P, P], color='red', alpha=0.75)

        self.conffig.plot([E, E], [0, P], color='red', alpha=0.75)

        self.confcanvas.draw()


class PyDP4WorkerObject(QtCore.QObject):
    finished = QtCore.pyqtSignal()

    def runPyDP4(self):
        launchdir = Path.cwd()

        print(ui.table_widget.Tab1.settings.OutputFolder)
        os.chdir(ui.table_widget.Tab1.settings.OutputFolder)

        self.log_file = open(ui.table_widget.Tab1.settings.OutputFolder/ "DP4_log.log" , "w+")

        self.NMRData, self.Isomers, self.settings, self.DP4Data = PyDP4.main(ui.table_widget.Tab1.settings)
        os.chdir(launchdir)
        self.finished.emit()


class WriteStream(object):
    def __init__(self, queue):
        self.queue = queue

    def write(self, text):
        self.queue.put(text)


class MyReceiver(QtCore.QObject):
    mysignal = QtCore.pyqtSignal(str)

    def __init__(self, queue, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.queue = queue

    @QtCore.pyqtSlot()
    def run(self):
        while True:
            text = self.queue.get()
            self.mysignal.emit(text)


def lorentzian(p, w, p0, A):
    x = (p0 - p) / (w / 2)
    L = A / (1 + x ** 2)

    return L


def ReadParamFile(f, t):
    infile = open(f, 'r')
    inp = infile.readlines()
    infile.close()

    if t not in inp[0]:
        print("Wrong parameter file type, exiting...")
        quit()

    if t == 'm':
        Cmeans = [float(x) for x in inp[1].split(',')]
        Cstdevs = [float(x) for x in inp[2].split(',')]
        Hmeans = [float(x) for x in inp[3].split(',')]
        Hstdevs = [float(x) for x in inp[4].split(',')]

        return Cmeans, Cstdevs, Hmeans, Hstdevs


q = queue.Queue()

sys.stdout = WriteStream(q)

app = QtWidgets.QApplication(sys.argv)

ui = Window()

ui.show()

thread = QtCore.QThread()
my_receiver = MyReceiver(q)
my_receiver.mysignal.connect(ui.table_widget.Tab1.append_text)
my_receiver.moveToThread(thread)
thread.started.connect(my_receiver.run)
thread.start()

sys.exit(app.exec_())


