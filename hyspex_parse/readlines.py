import numpy as np
from PIL import Image
import os

#adapted from https://github.com/StrawsonDesign/hyspex_viewer/
def readBIL(fname,orig_bands,readmode='lines',update_arr = None,step=1):
    #must read in ascending order
    order = np.argsort(orig_bands)
    bands = np.array(orig_bands)[order]
    hyspex_f = open(fname,"rb")
    header = hyspex_f.read(8)
    assert header == b'HYSPEX\x00\x00'
    head_size = np.fromstring(hyspex_f.read(4),'int32')[0]
    
    hyspex_f.seek(1949,os.SEEK_CUR)
    #number of channels and pixels
    spectral,spatial = np.fromstring(hyspex_f.read(8),'int32')
    hyspex_f.seek(4*26,os.SEEK_CUR)
    #number of lines in image
    number = np.fromstring(hyspex_f.read(4),'int32')[0]
    if update_arr:
        update_arr[1] = int(number)
    hyspex_f.seek(head_size,os.SEEK_SET)

    out_arr = np.empty([len(bands),spatial//step,number//step],dtype='uint16')
    #number of pixels we must step through to get from one channel to the next
    final_step = spectral-bands[-1]
    curr_pos = head_size
    band_cycle = [bands[0]-1]+list(np.diff(bands)-1)
    if readmode == 'mmap':
        #mmap the whole file
        mmaped_data = np.memmap(hyspex_f,dtype='uint16',mode='r',offset=curr_pos)
        mmaped_data.shape = (number,spectral,spatial)
        #extract the appropriate bands
        for i in range(0,number,step):
            if(i/step>=out_arr.shape[2]):
                break
            if update_arr:
                update_arr[0]=int(i)
                #check for poison pill
                if update_arr[1]==-1:
                    raise RuntimeError("I've been poisoned!")
            for b,band in enumerate(bands):
                out_arr[b,:,i//step]=mmaped_data[i,band-1,::step]
        return out_arr[order,:,:]

def processBand(band,idx):
    #adjust band to appear as true-color as possible
    band = band.astype('float32')
    lo_bound, hi_bound = np.percentile(band,[5,95])
    print(lo_bound,hi_bound)
    band[band < lo_bound] = lo_bound
    band[band > hi_bound] = hi_bound
    stretch = ((1<<16)-1)/(hi_bound-lo_bound)
    band -= lo_bound
    band *= stretch
    #old_max = band.max()
    #band *= [5.,5.,7.][idx]
    #band[band>old_max] = old_max
    return band


PROCESS_FUNCTIONS = {
        'VNIR':processBand,
        'SWIR':processBand,
}
def toGeoTiff(fname,rgb_arr,wlens="VNIR"):
    bands,rows,cols = rgb_arr.shape
    arr_8bit = np.empty([rows,cols,bands],dtype='uint8')
    #float_arr = processPercentile(rgb_arr)
    for b in range(bands):
        pband = PROCESS_FUNCTIONS.get(wlens,lambda x,y:x)(rgb_arr[b,:,:],b)
        arr_8bit[:,:,b] = (pband//256).astype('uint8')
    im = Image.fromarray(arr_8bit,mode='RGB')
    im.save(fname)

    '''
    driver = gdal.GetDriverByName("GTiff")
    bands,rows,cols= rgb_arr.shape
    out = driver.Create(fname,cols,rows,bands,gdal.GDT_UInt16,
            options = ['PHOTOMETRIC=RGB','PROFILE=GeoTIFF',])
    for b in range(bands):
        out.GetRasterBand(b+1).WriteArray(processBand(rgb_arr[b,:,:],b))
        out.GetRasterBand(b+1).FlushCache()
    '''


if __name__=='__main__':
    import sys
    if sys.argv[2] == '1':
        bands = readBIL(sys.argv[1],[19,46,75],sys.argv[3])
        toGeoTiff("test.png",bands)
    else:
        bands = readBIL(sys.argv[1],75)

