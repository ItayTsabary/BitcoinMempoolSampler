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
from random import randint



data_dir_path = ""
sleepInterval = 5
sleepInterval = 1 

def get_dir_path():
  return data_dir_path  


def get_sampling_properties():
  return sleepInterval


def make_tarfile(output_filename, source_dir):
  with tarfile.open(output_filename, "w:gz") as tar:
    tar.add(source_dir, arcname=os.path.basename(source_dir))
    
def compress_file(file_path):
  #filename, _ = os.path.splitext(file_path)
  filename = file_path
  output_filename = filename + ".tar.gz"
  make_tarfile(output_filename,file_path)
  

def compress_and_delete_file(output_folder_name,output_file_name):
  dir_path = get_dir_path()
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

def create_out_dir(dir_path):
  if not os.path.exists(dir_path):
      try:
          os.makedirs(dir_path)
      except OSError as exc: # Guard against race condition
          if exc.errno != errno.EEXIST:
              raise


def output_folder_and_file_names(block_count):
  
  current_time = time.strftime("%Y_%m_%d_%H_%M_%S")

  output_file_name = str(block_count) + "_" + current_time + ".log"      
  dir_path = get_dir_path()
  create_out_dir(dir_path)
  return dir_path,output_file_name
              

def write_output_file(output_folder_name,output_file_name,events_dict):

  # sort all the samples based on their timestamps
  soreted_time_stamps = sorted(events_dict.keys())


  dir_path = get_dir_path()
  file_path = os.path.join(dir_path,output_file_name)
  f = open(file_path, 'wb')


  print "there are ",len(soreted_time_stamps),"time stamps"

  for key in soreted_time_stamps:
      f.write("timestamp\n")
      stringToWrite = str(key) + "\n"
      f.write(stringToWrite)
      #print "timestamp",key
      addedTxsEventDict = events_dict[key]
      
      f.write("added\n")
      for key,value in addedTxsEventDict.items():
          #print "key",key,"value",value
          stringToWrite = str(key) + ":" + str(value) + "\n"
          f.write(stringToWrite)
      
      f.write("removed\n")

  f.close()
  print os.path.abspath(file_path) , " created " 


def is_new_file_needed(old_mempool, new_mempool):
  # check if any tx's were removed from the new mempool
  return not (set(old_mempool.keys()).issubset(new_mempool.keys()))


def list_of_added_transaction_keys(old_mempool, new_mempool):
  return list(set(new_mempool.keys()) - set(old_mempool.keys()))




def create_file(events_dict,block_count):
  # create folder
  output_folder_name,output_file_name = output_folder_and_file_names(block_count)

  #write file
  write_output_file(output_folder_name, output_file_name, events_dict)
      
  #tar gz and delete file
  compress_and_delete_file(output_folder_name,output_file_name)



def compare_three_numbers(a,b,c):
  return (a == b == c)


def main(config):
  bitcoinCoreConnection = connect_to_node(config)
  sleepInterval = get_sampling_properties()

  
  # these two dicts keep track of what happened in the previous iteration
  old_mempool = {}
  events_dict = {}
  previous_block_count = 0
  
  while True:
      #print "start of new outer iteration"

      current_time_sample = time.time()
      # get data from bitcoin core client
      try:
          block_count_pre = bitcoinCoreConnection.getblockcount()
          new_mempool = bitcoinCoreConnection.getrawmempool(verbose=True)
          block_count_post = bitcoinCoreConnection.getblockcount()          
      except _wrap_exception:
          print "caught exception " +  str(_wrap_exception) + " at time " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
          time.sleep(sleepInterval)
          continue
      except Exception:
          print "caught exception " +  str(Exception) + " at time " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
          time.sleep(sleepInterval)
          continue        


      if (not is_new_file_needed(old_mempool, new_mempool) and compare_three_numbers(block_count_pre,block_count_post,previous_block_count)):
        # list of new txs in mempool
        added_txs_names_list = list_of_added_transaction_keys(old_mempool, new_mempool)
        # dict of all new txs in mempool
        added_tx_details_dict = dict([(key, value) for key, value in new_mempool.items() if key in added_txs_names_list])
        # record time, block count and new tx data
        events_dict[current_time_sample] = added_tx_details_dict
        # sleep
        time.sleep(sleepInterval)
      else:
        create_file(events_dict,previous_block_count)
        #cleanups for the next iteration
        events_dict.clear()    
      
      previous_block_count = block_count_post
      old_mempool = new_mempool
      #end of "while true"


if __name__== "__main__":

  config = configparser.ConfigParser()
  config.read('sampler_config.ini')
  data_dir_path = config["output"]["data_dir_path"]

  main(config)

    

