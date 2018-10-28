'''
Created on 19 July 2017

@author: Itay
'''

import platform
import time 
import os
import errno
from bitcoinrpc import connection 
import operator
from bitcoinrpc.exceptions import _wrap_exception
import tarfile
import os.path
import shutil
import configparser


data_dir_path = ""
maxSamplesInFile = 1000
maxLinesInFile = 50000
sleepInterval = 5

#maxSamplesInFile = 10
#maxLinesInFile = 500
#sleepInterval = 1 

def get_dir_path(folderName):
  return data_dir_path  


def get_sampling_properties():
  return maxSamplesInFile,maxLinesInFile,sleepInterval


def make_tarfile(output_filename, source_dir):
  with tarfile.open(output_filename, "w:gz") as tar:
    tar.add(source_dir, arcname=os.path.basename(source_dir))
    
def compress_file(file_path):
  #filename, _ = os.path.splitext(file_path)
  filename = file_path
  output_filename = filename + ".tar.gz"
  make_tarfile(output_filename,file_path)
  

def compress_and_delete_file(output_folder_name,output_file_name):
  dir_path = get_dir_path(output_folder_name)
  file_path = os.path.join(dir_path,output_file_name)
  compress_file(file_path)
  os.remove(file_path)



def connect_to_node(config):

  username = config["server"]["username"]
  password = config["server"]["password"]
  hostip = config["server"]["hostip"]
  portnum = config["server"]["portnum"]

  bitcoinCoreConnection = connection.BitcoinConnection(username, 
                                                password,
                                                host=hostip, 
                                                port=portnum) 
  return bitcoinCoreConnection

def create_out_dir(dirPath):
  if not os.path.exists(dirPath):
      try:
          os.makedirs(dirPath)
      except OSError as exc: # Guard against race condition
          if exc.errno != errno.EEXIST:
              raise


def output_folder_and_file_names(firstSampleTime):
  output_folder_name = firstSampleTime[0:10]
  output_file_name = firstSampleTime[11:] + ".log"      
  
  dir_path = get_dir_path(output_folder_name)
  create_out_dir(dir_path)
  return output_folder_name,output_file_name
              

def write_output_file(output_folder_name,output_file_name,soretedTimeStamps, recordedBlockCountDict,recordedAddEventsDict,recordedRemoveEventsDict):
  dir_path = get_dir_path(output_folder_name)
  file_path = os.path.join(dir_path,output_file_name)
  f = open(file_path, 'wb')

  for key in soretedTimeStamps:
      f.write("timestamp\n")
      stringToWrite = str(key) + "-" + str(recordedBlockCountDict[key]) + "\n"
      f.write(stringToWrite)
      
      addedTxsEventDict = recordedAddEventsDict[key]
      removedTxsEventDictd = recordedRemoveEventsDict[key]
      
      f.write("added\n")
      for txName in addedTxsEventDict.keys():
          txData = addedTxsEventDict[txName]
          stringToWrite = str(txName) + str(txData) + "\n"
          f.write(stringToWrite)
      
      f.write("removed\n")
      for txName in removedTxsEventDictd.keys():
          txData = removedTxsEventDictd[txName]
          stringToWrite = str(txName) + str(txData) + "\n"
          f.write(stringToWrite)                        
   
          
  f.close()
  print os.path.abspath(file_path) , " created " 


def main(config):
  bitcoinCoreConnection = connect_to_node(config)
  maxSamplesInFile,maxLinesInFile,sleepInterval = get_sampling_properties()

  
  # these two dicts keep track of what happened in the previous iteration
  oldTxsInMempool = {}
  newTxsInMempool = {}
  
  while True:
      #print "start of new outer iteration"
      firstSampleTime = 0
      samplesCounter = 0
      approxLinesInFile = 0
      recordedBlockCountDict = {}
      recordedAddEventsDict = {}
      recordedRemoveEventsDict = {}
  
      while samplesCounter < maxSamplesInFile and approxLinesInFile < maxLinesInFile:
          #print "start of new inner iteration" , samplesCounter , maxSamplesInFile , approxLinesInFile , maxLinesInFile
          # these two dicts help us keep track of changes in the current iteration
          addedTxsEventDict = {}
          removedTxsEventDict = {}
          
          # record the time of current iteration
          sampleTime = time.time()
          # get data from bitcoin core client
          try:
              blockCount = bitcoinCoreConnection.getblockcount()
              verboseRawMemPool = bitcoinCoreConnection.getrawmempool(verbose=True)
          except _wrap_exception:
              print "caught exception " +  str(_wrap_exception) + " at time " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
              time.sleep(sleepInterval)
              continue
          except Exception:
              print "caught exception " +  str(Exception) + " at time " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
              time.sleep(sleepInterval)
              continue        
              
              
          # check which txs already existed
          for currentTxName in verboseRawMemPool: 
              # add to new dict
              newTxsInMempool[currentTxName] = verboseRawMemPool[currentTxName]
              if currentTxName in oldTxsInMempool:
                  # remove from old dict
                  del oldTxsInMempool[currentTxName]
                  #print "removed " , currentTxName , " from oldTxsInMempool which is now of length " , len(oldTxsInMempool)
              else:
                  # mark as a new tx
                  addedTxsEventDict[currentTxName] = verboseRawMemPool[currentTxName]
                  #print "added " , currentTxName , " to addedTxsEventDict which is now of length " , len(addedTxsEventDict)
  
         
          # check if old txs no longer exist
          for currentTxName in oldTxsInMempool.keys(): 
              # add to new dict
              removedTxsEventDict[currentTxName] = oldTxsInMempool[currentTxName]
              #print "added " , currentTxName , " to removedTxsEventDict which is now of length " , len(removedTxsEventDict)
              del oldTxsInMempool[currentTxName]
              #print "removed " , currentTxName , " from oldTxsInMempool which is now of length " , len(oldTxsInMempool)
  
          assert len(oldTxsInMempool) == 0
  
          recordedBlockCountDict[sampleTime] = blockCount
          recordedAddEventsDict[sampleTime]  = addedTxsEventDict
          recordedRemoveEventsDict[sampleTime] = removedTxsEventDict
  
          #   mark first sample   
          if firstSampleTime == 0:
              firstSampleTime = time.strftime("%Y_%m_%d_%H_%M_%S")
      
          #   prepare for next iteration
          samplesCounter = samplesCounter + 1
          approxLinesInFile = approxLinesInFile + len(addedTxsEventDict) + len(removedTxsEventDict)
          time.sleep(sleepInterval)
          oldTxsInMempool = newTxsInMempool
          newTxsInMempool = {}
          
          #end of " while samplesCounter < maxSamplesInFile and approxLinesInFile < maxLinesInFile:"

      # sort all the samples based on their timestamps
      soretedTimeStamps = sorted(recordedAddEventsDict.keys())
      
      #create folder
      output_folder_name,output_file_name = output_folder_and_file_names(firstSampleTime)

      #write file
      write_output_file(output_folder_name, output_file_name, soretedTimeStamps, recordedBlockCountDict,recordedAddEventsDict,recordedRemoveEventsDict)
      
      #tar gz and delete file
      compress_and_delete_file(output_folder_name,output_file_name)

      #cleanups for the next iteration
      del soretedTimeStamps[:]
      addedTxsEventDict.clear()    
      recordedAddEventsDict.clear()
      recordedRemoveEventsDict.clear()

      #end of "while true"


if __name__== "__main__":

  config = configparser.ConfigParser()
  config.read('sampler_config.ini')
  data_dir_path = config["output"]["data_dir_path"]

  main(config)

    

