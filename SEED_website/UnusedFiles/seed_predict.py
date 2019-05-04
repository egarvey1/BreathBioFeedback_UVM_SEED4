#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  2 16:12:21 2019

@author: alice
"""

# IMPORT LIBRARIES
from keras.models import Sequential
from keras.layers.core import Activation, Flatten, Dense, Dropout
import keras
import numpy as np
import matplotlib.pyplot as plt
import sqlite3
import os.path
from keras.optimizers import SGD
from sklearn.feature_extraction import DictVectorizer
import pickle
import matplotlib.pyplot as plt
from dataprep import *
from keras.models import model_from_json
K = keras.backend
np.set_printoptions(threshold=3)

# In[]: create funtion to quantify model performance

def f1_score(y_true, y_pred):
    # Count positive samples.
    c1 = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    c2 = K.sum(K.round(K.clip(y_pred, 0, 1)))
    c3 = K.sum(K.round(K.clip(y_true, 0, 1)))
    # If there are no true samples, fix the F1 score at 0.
    if c3 == 0:
        return 0
    # How many selected items are relevant?
    precision = c1 / c2
    # How many relevant items are selected?
    recall = c1 / c3
    # Calculate f1_score
    f1_score = 2 * (precision * recall) / (precision + recall)
    return f1_score 
            
# In[]: create funtion to access db files and extract data samples and labels
            
def open_db(db_file):
    global labels, data_path
    db_file=db_file
    db_name='/Users/alice/Desktop/'+db_file
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    ans=c.execute("SELECT datatype FROM Raw_Output_Data")
    labels=ans.fetchall() 
    c.execute("SELECT raw_output_data FROM Raw_Output_Data")
    data_path=c.fetchall()
    conn.close()
    return labels, data_path

# In[]: create funtion to randomize the order of samples and one hot encode signal labels

def seed_onehot(labels,signal_sections):    
    global onehot, rand_labels, rand_signal
    onehot=[]
    for i in range(0,len(labels)):
        if 'gup' in labels[i]:
            onehot.append((0,0,0,0,1))
        if 'talk' in labels[i]:
            onehot.append((0,0,0,1,0))
        if 'breath_in' in labels[i]:
            onehot.append((0,0,1,0,0))
        if 'breath_out' in labels[i]:
            onehot.append((0,1,0,0,0)) 
        if 'swallow' in labels[i]:
            onehot.append((1,0,0,0,0)) 
    indices=np.arange(0,len(signal_sections))
    np.random.shuffle(indices)
    rand_labels=[]
    rand_signal=[]
    for l in range(0,len(indices)):
        m=indices[l]
        rand_labels.append(onehot[m])
        rand_signal.append(signal_sections[m])
    return rand_labels, rand_signal, onehot

# In[]: create funtion to section training, testing, and validation groups of samples

def splitdata(rand_signal,onehot,train_percent,val_percent,test_percent):
    global xtrain,xval,xtest,ytrain,yval,ytest
    datasetsize=np.size(signal)
    train_size=int(train_percent*datasetsize)
    val_size=int(val_percent*datasetsize)
    test_size=int(test_percent*datasetsize)
    xtrain=np.array(rand_signal[0:train_size])
    xval=np.array(rand_signal[train_size:(train_size+val_size)])
    xtest=np.array(rand_signal[(train_size+val_size):])
    ytrain=np.array(onehot[0:train_size])
    yval=np.array(onehot[train_size:(train_size+val_size)])
    ytest=np.array(onehot[(train_size+val_size):])
    return xtrain,xval,xtest,ytrain,yval,ytest

# In[]: gather labeled samples

[labels, data_path]=open_db(db_file='//////////.db')

# In[]: show signals of one type

#plot1type(data_path=data_path,labeltype='gup',labels=labels)

# In[]: load original signal

data_comb=[]
# x,y,z data from accel
accx=[] 
accy=[]
accz=[]
# x,y,z data from gyro
gyrox=[]
gyroy=[]
gyroz=[]
# data from chest band
band=[]
# movement label
#label=[]


for i in range(0,len(data_path)):
    sample=data_path[i]
    sample_name=str(sample)
    name=sample_name[2:-3]
    f='////////////'+name
    current_label=labels[i]
    with open(f, 'rb') as f:
        data_array=pickle.load(f)
        accx=(data_array[:,0])
        accy=(data_array[:,1])
        accz=(data_array[:,2])
        gyrox=(data_array[:,3])
        gyroy=(data_array[:,4])
        gyroz=(data_array[:,5])
        band=(data_array[:,6])
        #label=np.tile(current_label,(len(data_array)))
        data_comb.append(np.c_[accx,accy,accz,gyrox,gyroy,gyroz,band])
 
# In[] truncate signal to create many samples of the same size


signal_section_size=30     # Define number of samples that will be considered during predictions

# Compile sections of signal
section_signals=[]      
section_labels=[]                # Label sections of signal

for x in range(0,len(data_comb)):
    numbits=int(np.floor((len(data_comb[x])-1)/signal_section_size)) # calculate number of new samples that will be created
    for y in range(0,numbits-1): # created new samples from original signal
        section_signals.append(data_comb[x][y*signal_section_size:(y+1)*signal_section_size,:])
        section_labels.append(np.tile(labels[x],(signal_section_size,1)))

        
# In[]: one hot encode and randomize new samples

[rand_labels, rand_signal, onehot] = seed_onehot(labels=section_labels,signal_sections=section_signals)


# In[]: split data into training, testing, and validation sets

[xtrain,xval,xtest,ytrain,yval,ytest]=splitdata(rand_signal=rand_signal,onehot=onehot,train_percent=0.7,val_percent=0.2,test_percent=0.1)

# In[]: load model

json_file = open('model.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
# load weights into new model
loaded_model.load_weights("model.h5")
print("Loaded model from disk")
 
# evaluate loaded model on test data
loaded_model.compile(loss='binary_crossentropy', optimizer='rmsprop', metrics=['accuracy'])
score = loaded_model.evaluate(xtest, ytest, verbose=0)
print("%s: %.2f%%" % (loaded_model.metrics_names[1], score[1]*100))
