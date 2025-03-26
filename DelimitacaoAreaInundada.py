from qgis.utils import iface
from qgis.core import QgsProcessing, QgsColorRampShader
import processing
import os, sys
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry

def area_inundada():
    # listar as camadas raster
    available_layers = [layer.name() for layer in QgsProject.instance().mapLayers().values() if layer.type()==QgsMapLayer.RasterLayer]

    if len(available_layers) == 0:
        print ('Não existem camadas raster disponíveis. Por favor carregue uma.')
        return

    # janela
    qid = QInputDialog()
    input_layer, ok_layer = QInputDialog.getItem(qid, 'Delimitacao de áre inundada', 'Selecione a camada:', available_layers)

    if ok_layer:
        input_level, ok_level = QInputDialog.getDouble(qid, 'Delimitacao de áre inundada', 'Introduza a cota:')
        if not ok_level:
            qid.close()
            return
    else:
        qid.close()
        return

    dtm_layer = QgsProject.instance().mapLayersByName(input_layer)[0]
    
    # criar caminho e nome para raster output
    # o novo ficheiro raster será gravado na pasta do raster original
    layer_absPath = dtm_layer.source()
    layer_basename = os.path.basename(layer_absPath)
    layer_pathname = os.path.dirname(layer_absPath)

    # verificar se a pasta para os resultados já existe
    input_level_str = str(input_level)
    if '.' in input_level_str:
        input_level_str=input_level_str.replace('.','_')
    elif ',' in input_level_str:
        input_level_str=input_level_str.replace(',','_')

    if not os.path.exists(layer_pathname+'/AreasInundadas'):
        os.mkdir(layer_pathname+'/AreasInundadas/')
                
    output_filename = layer_pathname+'/AreasInundadas/L'+input_level_str+'_'+layer_basename

    # calculo da area inundada
    layer = QgsRasterLayer(layer_absPath, 'dtm')
    if not layer.isValid():
        print('Erro a carregar o raster!')
        return
        
    band = QgsRasterCalculatorEntry()
    band.ref = layer.name() + '@1'
    band.raster = layer
    band.bandNumber = 1
        
    # calculo
    expression = '("'+band.ref+'" <= '+ str(input_level) + ') * 1 '
    print(expression)
    calc = QgsRasterCalculator(expression, 
                            output_filename, 
                            'GTiff',
                            layer.extent(),
                            layer.width(),
                            layer.height(),
                            [band])
                            
    rast = None
    resp = None
    
    calc.processCalculation()
    
    # carregar o novo raster no qgis
    rlayer = QgsRasterLayer(output_filename, os.path.basename(output_filename))
    if not rlayer.isValid():
        print("Layer failed to load!")
    else:
        #load new raster
        QgsProject.instance().addMapLayer(rlayer)
        # colorir o raster - agua azul o resto transparente
        fnc = QgsColorRampShader()
        fnc.setColorRampType(QgsColorRampShader.Exact)
        lst = [QgsColorRampShader.ColorRampItem(1, QColor(0,0,255)),\
        QgsColorRampShader.ColorRampItem(0, QColor(0,0,0,0))]
        fnc.setColorRampItemList(lst)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(fnc)
        renderer = QgsSingleBandPseudoColorRenderer(rlayer.dataProvider(), 1, shader)
        rlayer.setRenderer(renderer)
                
        rlayer = None


# call main function
area_inundada()
print('Processo terminado.')