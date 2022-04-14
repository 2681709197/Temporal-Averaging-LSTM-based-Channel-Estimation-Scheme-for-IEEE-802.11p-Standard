import torch
import os
import numpy as np
import torch.nn as nn
import pickle
import sys
import scipy
from scipy.io import loadmat
from sklearn.preprocessing import StandardScaler
import functions as fn
class LSTM_MLP(nn.Module):
    def __init__(self, input_size, lstm_size):
        super(LSTM_MLP, self).__init__()
        self.input_size = input_size
        self.lstm_size = lstm_size
        self.lstmcell = nn.LSTMCell(input_size=self.input_size,
                                    hidden_size=self.lstm_size)
        self.out = nn.Sequential(
            nn.ReLU(),
            nn.Linear(self.lstm_size, 40),
            nn.ReLU(),
            nn.Linear(40, 96)
        )

    def forward(self, x_cur, h_cur=None, c_cur=None):
        batch_size, _ = x_cur.size()
        if h_cur is None and c_cur is None:
            h_cur = torch.zeros(batch_size, self.lstm_size, device=x_cur.device)
            c_cur = torch.zeros(batch_size, self.lstm_size, device=x_cur.device)
        h_next, c_next = self.lstmcell(x_cur, (h_cur, c_cur))
        out = self.out(h_next)

        return out, h_next, c_next


scheme = 'DPA'
DL_Type = 'LSTM_DNN'
mobility = sys.argv[1]  # 'VH'
modu = sys.argv[2]  # 'QPSK'
SNR_index = np.arange(1, 10)
modu_way = 1
dposition = [0,1,2,3,4,5,7,8,9,10,11,12,13,14,15,16,17,18,19,21,22,23,24,25,26,27,28,29,30,32,33,34,35,36,37,38,39,40,41,42,43,44,46,47,48,49,50,51,56,57,58,59,60,61,63,64,65,66,67,68,69,70,71,72,73,74,75,77,78,79,80,81,82,83,84,85,86,88,89,90,91,92,93,94,95,96,97,98,99,100,102,103,104,105,106,107]
DSC_IDX  = np.array(dposition)
for n_snr in SNR_index:

    mat = loadmat('./{}/{}/{}_{}_Testing_Dataset_{}.mat'.format(mobility, modu, scheme,DL_Type, n_snr))
    Testing_Dataset = mat['Channel_Error_Correction_Dataset']
    Testing_Dataset = Testing_Dataset[0, 0]

    X = Testing_Dataset['Test_X']
    Y = Testing_Dataset['Test_Y']
    yf_d = Testing_Dataset['Y_DataSubCarriers']

    print('Loaded Dataset Inputs: ', X.shape)
    print('Loaded Dataset Outputs: ', Y.shape)
    print('Loaded Testing OFDM Frames: ', yf_d.shape)
    hf_DL = np.zeros((yf_d.shape[0], yf_d.shape[1], yf_d.shape[2]), dtype="complex64")
    device = torch.device("cpu")
    NET = torch.load('D:/ChPrediction/{}_{}_{}_{}_Trained_Model_40.pkl'.format(mobility, modu, scheme, DL_Type)).to(device)
    scaler = StandardScaler()

    # For over all Frames
    for i in range(yf_d.shape[0]):
        hf = X[i, 0, :]
        hn, cn = None, None
        print('Testing Frame | ', i)
        # For over OFDM Symbols
        for j in range(yf_d.shape[1]):
            hf_input = hf
            input1 = scaler.fit_transform(hf_input.reshape(-1, 2)).reshape(hf_input.shape)
            input2 = torch.from_numpy(input1).type(torch.FloatTensor).unsqueeze(0)
            output, hn, cn = NET(input2.to(device), hn, cn) # ([1,96])
            out = scaler.inverse_transform(output.detach().cpu().numpy().reshape(-1, 2)).reshape(output.shape)
            hf_out = out[:, :48] + 1j * out[:, 48:] # (1,48)
            hf_DL[i, j, :] = hf_out
            sf = yf_d[i, j, :] / hf_out # (1,48)
            x = fn.demap(sf, modu_way)
            xf = fn.map(x, modu_way)
            hf_out = yf_d[i, j, :] / xf
            hf_out = hf_out.ravel()
            hf_out_Expanded = np.concatenate((hf_out.real, hf_out.imag), axis=0)
            if j < yf_d.shape[1] - 1:
                X[i, j + 1, DSC_IDX] = hf_out_Expanded
                hf = X[i, j + 1, :]# (48,)
    # Save Results
    result_path = './{}/{}/{}_{}_Results_{}.pickle'.format(mobility, modu, scheme, DL_Type, n_snr)
    dest_name = './{}/{}/{}_{}_Results_{}.mat'.format(mobility, modu, scheme, DL_Type, n_snr)
    with open(result_path, 'wb') as f:
        pickle.dump([X, Y, hf_DL], f)

    a = pickle.load(open(result_path, "rb"))
    scipy.io.savemat(dest_name, {
        '{}_test_x_{}'.format(scheme, n_snr): a[0],
        '{}_test_y_{}'.format(scheme, n_snr): a[1],
        '{}_corrected_y_{}'.format(scheme, n_snr): a[2]
    })
    print("Data successfully converted to .mat file ")
    os.remove(result_path)





