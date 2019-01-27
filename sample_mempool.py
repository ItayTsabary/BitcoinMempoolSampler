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
import traceback
import configparser
from random import randint



data_dir_path = ""
sleepInterval = 10


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
  file_path = os.path.join(output_folder_name,output_file_name)
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
def round_down(num, divisor):
  return num - (num%divisor)

def output_folder_and_file_names(current_time_sample,block_count_pre,block_count_post):
  output_file_name = str(block_count_pre) + "_" + str(block_count_post) + "_" + current_time_sample + ".log"
  rounded_block_number = round_down(block_count_pre,100)
  dir_path = os.path.join(get_dir_path(),str(rounded_block_number))
  create_out_dir(dir_path)
  return dir_path,output_file_name


def write_output_file(output_folder_name, output_file_name, mempool):
  file_path = os.path.join(output_folder_name,output_file_name)
  f = open(file_path, 'wb')
  f.write(str(mempool))
  f.close()
  print os.path.abspath(file_path) , " created "






def  create_file(current_time_sample,block_count_pre,block_count_post,mempool):
  # create folder
  output_folder_name,output_file_name = output_folder_and_file_names(current_time_sample,block_count_pre,block_count_post)

  #write file
  write_output_file(output_folder_name, output_file_name, mempool)

  #tar gz and delete file
  compress_and_delete_file(output_folder_name,output_file_name)



def compare_three_numbers(a,b,c):
  return (a == b == c)


def main(config):
  bitcoinCoreConnection = connect_to_node(config)
  sleepInterval = get_sampling_properties()

  while True:
      #print "start of new outer iteration"

      current_time_sample = time.strftime("%Y_%m_%d_%H_%M_%S")
      # get data from bitcoin core client
      try:
          block_count_pre = bitcoinCoreConnection.getblockcount()
          mempool = bitcoinCoreConnection.getrawmempool(verbose=True)
          block_count_post = bitcoinCoreConnection.getblockcount()
          create_file(current_time_sample,block_count_pre,block_count_post,mempool)
      except _wrap_exception as e:
          print "caught exception {} at time {}".format(traceback.print_exc(e), time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
      except Exception as e:
          print "caught exception {} at time {}".format(traceback.print_exc(e), time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))


      time.sleep(sleepInterval)
      #end of "while true"


if __name__== "__main__":

  config = configparser.ConfigParser()
  config.read('sampler_config.ini')
  data_dir_path = config["output"]["data_dir_path"]

  main(config)



