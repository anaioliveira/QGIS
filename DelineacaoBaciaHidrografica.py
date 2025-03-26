# Developed by Ana Ramos Oliveira

# imports
from PyQt5.QtCore import Qt
from qgis.utils import iface
from qgis.core import QgsProcessing, QgsColorRampShader, QgsPointXY
from qgis.gui import QgsMapTool
import os, sys

# class to store the outlet coordinates 
class GetPointCoordinates(QgsMapTool):
    def __init__(self, canvas, layer):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.point = None
        self.loop = None  # Event loop to pause execution

    def canvasPressEvent(self, event):
        self.point = self.toLayerCoordinates(self.layer, event.pos()) # Store the clicked point
        
        # Exit the event loop after the first click
        if self.loop:
            self.loop.quit()

# function to get coordinates of a point by clicking on canvas
def get_clicked_point(layer):
    
    # get canvas
    canvas = iface.mapCanvas()
    # create class
    point_tool = GetPointCoordinates(canvas, layer)
    canvas.setMapTool(point_tool)

    # Create and start the event loop
    loop = QEventLoop()
    point_tool.loop = loop # Store the loop in the tool
    loop.exec_() # Wait until the user clicks

    return point_tool.point  # Return the clicked point
    
# function so load raster and shapefiles
def load_raster(rasters_to_load):
    # carregar raster no qgis
    for ras in rasters_to_load:
        rlayer = QgsRasterLayer(ras, os.path.basename(ras))
        if not rlayer.isValid():
            print("Layer failed to load!")
        else:
            #load new raster
            QgsProject.instance().addMapLayer(rlayer)
                    
            rlayer = None

# applying r.watershed process
def raster_watershed_process(dtm_layer):
    
    # create path for raster output - saved in the directory where the dtm is stored
    layer_absPath = dtm_layer.source()
    layer_basename = os.path.basename(layer_absPath)
    layer_pathname = os.path.dirname(layer_absPath)
    
    if not os.path.exists(layer_pathname+'/DelinBacia'):
        os.mkdir(layer_pathname+'/DelinBacia/')
                
    # create of drainage network direction and accumulation
    output_filename_acc = layer_pathname+'/DelinBacia/'+'Acu_'+layer_basename
    output_filename_dn = layer_pathname+'/DelinBacia/'+'DNDir_'+layer_basename
    fillParameters = { 'elevation' : layer_absPath, \
                       's' : False, \
                       'm' : False, \
                       '4' : False, \
                       'a' : False, \
                       'b' : False, \
                       'overwrite' : True, \
                       'accumulation' : output_filename_acc, \
                       'drainage' : output_filename_dn, \
                       'convergence' : 5, \
                       'memory' : 300}
    
    # change cursor to wait cursor
    QApplication.setOverrideCursor(Qt.WaitCursor)
    processing.run('grass7:r.watershed', fillParameters)
    # load resulting rasters (drainage direction and accumulation)
    load_raster([output_filename_dn, output_filename_acc])
    # restore cursor
    QApplication.restoreOverrideCursor()

    return output_filename_dn

# applying r.water.outlet process
def raster_watershed_outlet_process(outlet_point, drain_dir_raster_layer):
    
    # create path to raster output - saved in the directory where the dtm is stored
    layer_pathname = os.path.dirname(drain_dir_raster_layer)
    output_filename_watershed = layer_pathname+'/'+'Watershed.tif'
    
    # get selected outlet coordinates
    point_list = list(outlet_point)
    coord = str(point_list[0])+','+str(point_list[1])
    fillParameters = { 'input' : drain_dir_raster_layer, \
                       'output' : output_filename_watershed, \
                       'coordinates' : coord, \
                       'distance_units' : 'meters', \
                       'area_units' : 'm2'}
    # change cursor to wait cursor
    QApplication.setOverrideCursor(Qt.WaitCursor)
    processing.run('grass7:r.water.outlet', fillParameters)
    # restore cursor
    QApplication.restoreOverrideCursor()
    
    return output_filename_watershed

# transform the resulting watershed into shapefile and cut the original dtm according to the shapefile
# the result is the dtm of the delineated watershed
def watershed_shp_dtm(dtm_layer, watershed_raster_file):
        
    #change cursor
    QApplication.setOverrideCursor(Qt.WaitCursor)
    
    #polygonize (raster to shp)
    raster = watershed_raster_file
    shp = watershed_raster_file.replace('tif','gpkg')
    
    fillParameters = { 'INPUT' : raster, \
                       'BAND' : 1, \
                       'OUTPUT' : shp, \
                       'FIELD' : 'DN'}
    processing.run('gdal:polygonize',fillParameters)

    # cut dtm
    output_file = os.path.dirname(raster) + '/' + 'Watershed_DTM.tif'
    fillParameters = { 'INPUT' : dtm_layer, \
                       'MASK' : shp, \
                       'SOURCE_CRS' : dtm_layer.crs().authid(), \
                       'TARGET_CRS' : dtm_layer.crs().authid(), \
                       'CROP_TO_CUTLINE' : True, \
                       'OUTPUT' : output_file}
    processing.run("gdal:cliprasterbymasklayer", fillParameters)
    # loading watershed dtm
    load_raster([output_file])
    # restore cursor
    QApplication.restoreOverrideCursor()
    
    return

def watershed_delineation():
    # construct list of raster layers available in qgis
    available_layers = [layer.name() for layer in QgsProject.instance().mapLayers().values() if layer.type()==QgsMapLayer.RasterLayer]
    
    if len(available_layers) == 0:
        print ('Não existem camadas raster disponíveis. Por favor carregue uma.')
        return
    
    # window to select original dtm raster
    qid = QInputDialog()
    input_layer, ok_layer = QInputDialog.getItem(qid, 'Delineação de bacia hidrográfica', 'Selecione a camada:', available_layers)
    
    if not ok_layer:
        qid.close()
        return
    
    dtm_layer = QgsProject.instance().mapLayersByName(input_layer)[0]

    # run r.watershed process to generate accumulated flow and direction flow
    drain_dir_raster_layer = raster_watershed_process(dtm_layer)
    
    # select outlet point
    outlet_point = get_clicked_point(dtm_layer)
    
    # run r.water.outlet process to delineate a basin according to selected outlet
    watershed_raster_file = raster_watershed_outlet_process(outlet_point, drain_dir_raster_layer)
    
    # polygonize raster watershed (to shp) and cut dtm accordingly
    watershed_shp_dtm(dtm_layer, watershed_raster_file)


# call main function
watershed_delineation()
#point_click(self, iface)
print('Processo terminado.')