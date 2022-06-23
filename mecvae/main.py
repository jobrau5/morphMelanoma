import tensorflow as tf
from tensorflow.keras import mixed_precision
from cvae import CVAE
import argparse
from os.path import join
import os

from utils import readingData, readingDataWithFileNames, createCallbacks, createDirectories

parser = argparse.ArgumentParser(description='')
parser.add_argument('--inputDir',       type=str,   default='/Users/jones/Downloads/test2',     help='input data directory (in train subfolder)')
parser.add_argument('--outputFilename',       type=str,   default='Output',     help='output 2 data directory (in train subfolder)')
#parser.add_argument('--saveDir',       type=str,   default='Outputs/',     help='save directory')

parser.add_argument('--earlystop',		type=int,	default=1,			help='use early stopping? 1=yes, 0=no')

parser.add_argument('--epochs',         type=int,   default=2,          help='training epochs')
parser.add_argument('--learnRate',     type=float, default=0.0001,      help='learning rate')
parser.add_argument('--latentDim',     type=int,   default=64,          help='latent dimension')
parser.add_argument('--interDim',      type=int,   default=128,        help='intermediate dimension')
parser.add_argument('--nlayers',        type=int,   default=3,          help='number of layers in models')
parser.add_argument('--nfilters',       type=int,   default=16,         help='num convolution filters')
parser.add_argument('--kernelSize',    type=int,   default=3,          help='number of convolutions')
parser.add_argument('--batchSize',     type=int,   default=16,         help='batch size')
parser.add_argument('--epsilonStd',    type=float, default=1.0,        help='epsilon width')


parser.add_argument('--imageSize',     type=int,   default=512,         help='image size')
parser.add_argument('--nchannel',       type=int,   default=3,          help='image channels')

parser.add_argument('--phase',          type=str,   default='train',    help='train or load')

args = parser.parse_args()

#layersList = [3,4]
#latentList = [128,64]
#test latentDim < interDim
#interDimList = [128, 64]
#kernelList = [3]
#learnRateList = [0.0001, 0.001]
#filtersList = [16, 32]
#for i in range(len(layersList)):
#    for j in range(len(latentList)):
#        for k in range(len(kernelList)):
#            args.nlayers = layersList[i]
#            args.latentDim = latentList[j]
#            args.kernelSize = kernelList[k]

def main():
    runNumber = 0
    if args.phase == 'train':
        args.saveDir = createDirectories(args.outputFilename)
        print('Created new Directory to store Output')
        # improve run time by splitting the data on multiple cores
        tf.debugging.set_log_device_placement(True)
        gpus = tf.config.list_logical_devices('GPU')
        print(gpus)
        mirrored_strategy = tf.distribute.MirroredStrategy(gpus)
        args.batchSize *= mirrored_strategy.num_replicas_in_sync
        train_ds, val_ds = readingData(args.inputDir,args.imageSize, args.batchSize, shuffle= True, validation = 0.1)
        print('Read in transformed images')
        callbacks = createCallbacks(args.saveDir, args.earlystop, args.nlayers, args.learnRate, args.latentDim, args.nfilters, args.kernelSize)
        print('Created callbacks')
        #improve run time a lot by calculating float16 instead of float 32
        mixed_precision.set_global_policy('mixed_float16')
        optimizer = tf.keras.optimizers.Adam(args.learnRate)
        #adjust optimizer to float16 instead of float 32
        optimizer = mixed_precision.LossScaleOptimizer(optimizer)

        print('Init model')
        model = CVAE(args)
        print('Compile model')
        model.compile(optimizer = optimizer, run_eagerly=True)
        print('Model compiled. model.fit starts')
        model.fit(train_ds, epochs = args.epochs, batch_size=args.batchSize, callbacks=callbacks)
        modelDir = os.path.join(args.saveDir, 'models')
        os.makedirs(modelDir, exist_ok=True)
        print('Save model weights to', modelDir)
        model.save_weights(join(modelDir, 'weights_CVAE.hdf5'))

        print('Model saved. Start encoding')
        image_ds, list_ds, imageCount = readingDataWithFileNames(args.inputDir,args.imageSize)
        model.encode(image_ds, list_ds, imageCount)
        print('DONE with Training and storing Embeddings!!')

    if args.phase == 'load':
        image_ds, imageCount = readingDataWithFileNames(args.inputDir,args.imageSize)
        print('Read in transformed images')
        if args.checkpoint == 'NA':
            sys.exit('No checkpoint file provided')
        model = MEVAE(args)
        model.vae.load_weights(args.checkpoint)
        model.encode(image_ds)


    runNumber += 1


if __name__ == '__main__':
    main()