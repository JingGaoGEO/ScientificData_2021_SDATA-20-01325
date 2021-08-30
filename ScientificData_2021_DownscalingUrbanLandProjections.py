import arcpy
arcpy.CheckOutExtension("spatial")

#### set parameters ####
currSSP = "ssp1" ## iterate through "ssp1", "ssp2", "ssp3", "ssp4", "ssp5"

## CONSTANT VARIABLES ##
# 1/8-dgr input path
inPath = "./UrbanFraction_1_8_dgr_GEOTIFF_Projections_SSPs1-5_2010-2100_v1/"
# 1-km output path
outPath = "./UrbanFraction_1km_GEOTIFF_Projections_SSPs1-5_2010-2100_v1/"
# scratch space path
arcpy.env.workspace = "./scratch/"

# constant map layers
fineLandAreaR = arcpy.Raster("1km_land_area_km2.tif")
coarseLandAreaR = arcpy.Raster("18dgr_land_area_km2.tif")
supScalerR = arcpy.Raster("SupScaler_forNoData.tif")

# ArcPy Environmental Variables
arcpy.env.extent = fineLandAreaR
arcpy.env.snapRaster = fineLandAreaR
arcpy.env.cellSize = fineLandAreaR
arcpy.env.compression = 'LZW'
arcpy.env.overwriteOutput = True


for endYr in range(2010, 2101, 10):
    beginYr = endYr-10
    coarseZoneR = arcpy.Raster("18dgrFishnet_in1km_forZonalStat.tif")
    flagR = arcpy.Raster("1km_flag_allZeros.tif")
    
    if endYr == 2010:
        fineFracR = arcpy.Raster("./UrbanFraction_1km_GEOTIFF_BaseYear_2000_v1/urb_frac_2000.tif")
    else: # i.e. endYr = 2020~2100
        fineFracR = arcpy.Raster(outPath+currSSP+"_"+str(beginYr)+".tif")
    fineAmtR = fineFracR * fineLandAreaR
    fineAmtR.save("temp_fineAmt.tif")
    del fineFracR

    coarseAmtR = arcpy.sa.ZonalStatistics(coarseZoneR, "VALUE", fineAmtR, "Sum")
    coarseAmtR.save("temp_coarseAmt_beginYr_forScaler.tif")
    scalerRawR = fineAmtR / coarseAmtR
    scalerRawR.save("temp_scalerWithNoData.tif")
    scalerR = arcpy.sa.Con(arcpy.sa.IsNull(scalerRawR), supScalerR, scalerRawR)
    scalerR.save("temp_scaler.tif")
    del scalerRawR

    coarseEndYrAmtR = arcpy.Raster(inPath+currSSP+"_"+str(endYr)+".tif") * coarseLandAreaR
    arcpy.management.Resample(coarseEndYrAmtR, "temp_coarseEndYrAmt_1km.tif", "0.008333333333", "NEAREST")
    coarseEndYrAmtR = arcpy.Raster("temp_coarseEndYrAmt_1km.tif")
    coarseChgAmtR = coarseEndYrAmtR - coarseAmtR
    coarseChgAmtR = arcpy.sa.Con(coarseChgAmtR > 0, coarseChgAmtR, 0)
    coarseChgAmtR.save("temp_coarseChgAmt.tif")
    del coarseEndYrAmtR, coarseAmtR

    LoopAllocate = True
    i = 0

    while LoopAllocate:
        i = i+1
        
        fineChgAmtR = coarseChgAmtR * scalerR
        fineChgAmtR.save("temp_fineChgAmt_"+str(i)+".tif")
        
        fineAmtR = fineAmtR + fineChgAmtR
        fineAmtR.save("temp_fineAmt_"+str(i)+".tif")
        del fineChgAmtR
        
        fineOverflowPreR = fineAmtR - fineLandAreaR
        fineOverflowR = arcpy.sa.Con(fineOverflowPreR > 0, fineOverflowPreR, 0)
        fineOverflowR.save("temp_fineOverflow_"+str(i)+"_0.tif")
        del fineOverflowPreR
        
        fineAmtR = arcpy.sa.Con(fineOverflowR > 0, fineLandAreaR, fineAmtR)
        fineAmtR.save("temp_fineAmt_loop_"+str(i)+".tif")

        if fineOverflowR.maximum > 0.000005:
            coarseChgAmtR = arcpy.sa.ZonalStatistics(coarseZoneR, "VALUE", fineOverflowR, "Sum")
            coarseChgAmtR = arcpy.sa.SetNull(coarseChgAmtR, coarseChgAmtR, "VALUE<=0")
            coarseChgAmtR.save("temp_coarseChgAmt_"+str(i)+".tif")
            
            coarseZoneR = arcpy.sa.Con(arcpy.sa.IsNull(coarseChgAmtR), coarseChgAmtR, coarseZoneR)
            coarseZoneR = arcpy.sa.Int(coarseZoneR)
            coarseZoneR.save("temp_coarseZone_"+str(i)+".tif")
            fineOverflowR = arcpy.sa.Con(arcpy.sa.IsNull(coarseChgAmtR), coarseChgAmtR, fineOverflowR)
            fineOverflowR.save("temp_fineOverflow_"+str(i)+"_1.tif")
            
            flagR = arcpy.sa.Con(arcpy.sa.IsNull(coarseChgAmtR), coarseChgAmtR, flagR)
            flagR = arcpy.sa.Con((flagR==0) & (fineOverflowR>0), 1, flagR)
            flagR.save("temp_flag_"+str(i)+".tif")
            
            scalerR = arcpy.sa.Con(arcpy.sa.IsNull(coarseChgAmtR), coarseChgAmtR, scalerR)
            scalerR = arcpy.sa.Con(flagR > 0, 0, scalerR)
            scalerR.save("temp_scaler_"+str(i)+"_0.tif")
            coarseScalerSumR = arcpy.sa.ZonalStatistics(coarseZoneR, "VALUE", scalerR, "Sum")
            coarseScalerSumR.save("temp_coarseScalerSum_"+str(i)+"_0.tif")
            scalerR = arcpy.sa.Con(coarseScalerSumR == 0, supScalerR, scalerR)
            scalerR = arcpy.sa.Con(flagR > 0, 0, scalerR)
            scalerR.save("temp_scaler_"+str(i)+"_1.tif")
            coarseScalerSumR = arcpy.sa.ZonalStatistics(coarseZoneR, "VALUE", scalerR, "Sum")
            coarseScalerSumR.save("temp_coarseScalerSum_"+str(i)+"_1.tif")

            scalerR = scalerR / coarseScalerSumR
            scalerR.save("temp_scaler_"+str(i)+".tif")

            del coarseScalerSumR, fineOverflowR
            
        else:
            LoopAllocate = False
            del coarseZoneR, scalerR, fineAmtR, flagR, coarseChgAmtR, fineOverflowR
            break

    rasterList = []
    for iterID in range(1, i+1, 1):
        rasterList.append("temp_fineAmt_loop_"+str(iterID)+".tif")

    fineAmtR = arcpy.sa.CellStatistics(rasterList, "MAXIMUM", "DATA")
    arcpy.management.CopyRaster(fineAmtR, "1km_amt_"+currSSP+"_"+str(endYr)+".tif")

    fineFracR = fineAmtR / fineLandAreaR
    arcpy.management.CopyRaster(fineFracR, (outPath+currSSP+"_"+str(endYr)+".tif"))

    del rasterList, fineAmtR, fineFracR
