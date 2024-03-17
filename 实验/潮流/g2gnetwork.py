
import numpy as np
import pandas as pd
import copy

import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten

from scipy.sparse import load_npz
from gat import GraphAttentionLayer as GAT


def PQ():
    isPQ = np.zeros((ori_case['bus'].shape[0],))
    wherePQ = np.where(ori_case['bus'][:,1]==1)[0]
    for i in range(wherePQ.shape[0]):
        isPQ[wherePQ[i]] = 1
    return isPQ

def PV():
    isPV = np.zeros((ori_case['bus'].shape[0],))
    wherePV = np.where(ori_case['bus'][:,1]==2)[0]
    for i in range(wherePV.shape[0]):
        isPV[wherePV[i]] = 1
    return isPV

def Pt():
    isPt= np.zeros((ori_case['bus'].shape[0],))
    wherePt = np.where(ori_case['bus'][:,1]==3)[0]
    for i in range(wherePt.shape[0]):
        isPt[wherePt[i]] = 1
    return isPt

def load_H(start_label,end_label,dataset='训练集',datatype='输入'):
    filepath = path + r'\数据\潮流(图)格式\1581节点系统\%s\%s'%(dataset,datatype)
    H_in = np.zeros((end_label-start_label,h_in_shape0,6))
    for _ in range(start_label,end_label):
        H_in[_,:,:] = np.load(filepath+r'\casezj_H_%s.npy'%_)
        print('\r加载进度%s/%s'%(_,end_label-start_label),end='\r')
    return H_in

def norm_H(H_in):
    # 对于每个节点的每种属性计算平均值和标准差
    mean_per_node = np.round(np.mean(H_in, axis=0),4)
    std_per_node = np.round(np.std(H_in, axis=0),4)
    
    # 创建一个与H_in形状相同的数组，用于存放标准化后的数据
    H_normalized_per_node = np.zeros_like(H_in)
    
    # 遍历每个节点的每种属性
    for i in range(H_in.shape[1]):  # 遍历所有节点
        for j in range(H_in.shape[2]):  # 遍历所有属性
            # 如果标准差不为零，则进行标准化
            if std_per_node[i, j] != 0:
                H_normalized_per_node[:, i, j] = (H_in[:, i, j] - mean_per_node[i, j]) / std_per_node[i, j]
            else:
                # 标准差为零时，只减去平均值
                H_normalized_per_node[:, i, j] = H_in[:, i, j] - mean_per_node[i, j]

    return H_normalized_per_node, mean_per_node, std_per_node

def create_model():
    # 定义模型
    
    hin = tf.keras.Input(shape=(1581,3),dtype=tf.complex128)
    
    #p_load_in = tf.math.real(hin[:,:,0])
    
    h_hidden = GAT(units=3, num_heads=8)([hin,Y])
    
    h_hidden = GAT(units=3, num_heads=8)([hin,Y])
    
    hout = GAT(units=3, num_heads=8,output_layer=True)([h_hidden,Y])

    #p_load_out = tf.math.real(hout[:,:,0])
    
    #loss1 = tf.reduce_mean(tf.math.abs(p_load_out * isPQ - p_load_in))
    
    
    model = tf.keras.Model([hin], [hout])
    model.compile(optimizer='adam',
              loss=complex_mean_squared_error,  # 假设是回归问题
              #metrics=['mean_absolute_error']
              )
    
    #loss = 2*loss1
    
    
    #model.add_metric(loss1,name='loss1')
    
    #model.add_loss(loss)
    
    return model

def floatH2complexH(H):
    col1_real = H[:, :, 0]
    col1_imag = H[:, :, 1]
    col2_real = H[:, :, 2]
    col2_imag = H[:, :, 3]
    col3_val = H[:, :, 4]
    col3_theta = H[:, :, 5]
    # 创建复数列
    col1_complex = tf.complex(col1_real, col1_imag)
    col2_complex = tf.complex(col2_real, col2_imag)
    
    theta_radians = np.radians(col3_theta)
    col3 = col3_val * np.exp(1j * theta_radians)
    # 将新的复数列与原始的前两列组合在一起
    H_complex = np.stack([col1_complex , col2_complex , col3], axis=2)
    return H_complex

def complex_mean_squared_error(y_true, y_pred):
    # 分别计算实部和虚部的平方误差
    real_diff = tf.math.real(y_pred) - tf.math.real(y_true)
    imag_diff = tf.math.imag(y_pred) - tf.math.imag(y_true)

    # 计算总的均方误差
    return tf.reduce_mean(tf.square(real_diff) + tf.square(imag_diff))

if __name__ == "__main__":
    
    """
    加载前置文件
    """
    ID_name_tab = pd.read_excel('flex_assessment_configs.xlsx', sheet_name='节点',index_col=0)
    
    branch_tab = pd.read_excel('flex_assessment_configs.xlsx', sheet_name='支路',index_col=0)
    
    outer_power_tab = pd.read_excel('flex_assessment_configs.xlsx', sheet_name='外来电',index_col=0)
    
    wind_tab = pd.read_excel('flex_assessment_configs.xlsx', sheet_name='风电',index_col=0)
    
    pv_tab = pd.read_excel('flex_assessment_configs.xlsx', sheet_name='光伏',index_col=0)
    
    nc_tab = pd.read_excel('flex_assessment_configs.xlsx', sheet_name='核电',index_col=0)
    
    load_tab = pd.read_excel('flex_assessment_configs.xlsx', sheet_name='负荷',index_col=0)
    
    flex_tab = pd.read_excel('flex_assessment_configs.xlsx', sheet_name='灵活资源',index_col=0)
    
    path = r'F:\预训练大模型'
    ori_case = {key: np.load(path+r'\实验\潮流\zj2025.npz')[key] for key in np.load('zj2025.npz')}
    
    isPQ = PQ()
    isPV = PV()
    isPt = Pt()
    
    total_sample_num = 1000   
    sample_for_each_iter = 1000
    
    h_in_shape0 = ID_name_tab.shape[0]
    
    Y = load_npz(path+r'\数据\潮流(图)格式\1581节点系统\测试集\输入\casezj_Y_0.npz').toarray()
    
    model = create_model()
    
    for i in range(int(total_sample_num/sample_for_each_iter)):
        
        H_in =  load_H(i*sample_for_each_iter,(i+1)*sample_for_each_iter)
        H_in_complex = floatH2complexH(H_in)
        H_in_norm,H_in_mean,H_in_std = norm_H(H_in_complex)
        
        H_out = load_H(i*sample_for_each_iter,(i+1)*sample_for_each_iter,'训练集','输出')
        H_out_complex = floatH2complexH(H_out)
        H_out_norm,H_out_mean,H_out_std = norm_H(H_out_complex)
        
        #model.fit(H_in_norm, H_out_norm, epochs=int(sample_for_each_iter/10), batch_size=int(sample_for_each_iter/10), validation_split=0.2,verbose=1)