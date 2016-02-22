# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 11:44:39 2016

@author: vpuller
"""

from __future__ import division
import numpy as np
from scipy import linalg as LA
from scipy import optimize
import matplotlib.pyplot as plt
import sys, os


sys.path.append('/ebio/ag-neher/share/users/vpuller/HIVEVO/HIVEVO_access') 
from hivevo.patients import Patient
from hivevo.HIVreference import HIVreference

h = 10**(-8)
cols_Fabio = ['b','c','g','y','r','m']
cols = ['b','g','r','c','m','y','k','b','g','r']

def curve_smu(smu,tt):
    return smu[1]/smu[0]*(1-np.exp(-smu[0]*tt))
    
def Covariance(p_ka):
    '''Covariance matrix and correlation coefficient'''
    pmean_k = p_ka.mean(axis=1); L = p_ka.shape[1]
    return (p_ka - np.tile(pmean_k,(L,1)).T).dot(p_ka.T - np.tile(pmean_k,(L,1)))/(L-1)    

def fit_upper(xka,t_k):
    '''Fitting the quantile data with a linear law'''
    def fit_upper_MLS(mu):
        chi2 = np.zeros(xk_q.shape)
        chi2 = (xk - mu*t_k).dot(xk - mu*t_k)/(L-1)
        return chi2
    xk = xka.mean(axis=1); L = xka.shape[1]
    res = optimize.minimize_scalar(fit_upper_MLS)
    return res.x


'''Kullback-Leibler fitting'''
def KLfit_simult_new_sigma(Ckqa,pmean_ka,t_k,Lq = None,sigma = None,gx = None):
    '''Simultaneous KL divergence minimization for several quantiles''' 
    def Kkq_gauss(s,D0):
        '''Correlation matrix'''
        t_kq = np.tile(t_k,(t_k.shape[0],1))
        dt_kq = np.abs(t_kq - t_kq.T)
        tmin_kq = (t_kq + t_kq.T -dt_kq)/2
        if s > h:
            return np.exp(-s*dt_kq)*(1. - np.exp(-2*s*tmin_kq))*D0/(2*s)
        else:
            return np.exp(-s*dt_kq)*(2*tmin_kq - 2*s*tmin_kq**2)*D0/2
    
    def Kkq_sqrt(s,mu,D0):
        '''Correlation matrix'''
        t_kq = np.tile(t_k,(t_k.shape[0],1))
        dt_kq = np.abs(t_kq - t_kq.T)
        tmin_kq = (t_kq + t_kq.T -dt_kq)/2
        if s > h:
            return np.exp(-s*dt_kq)*(1. - np.exp(-s*tmin_kq))*mu*D0/(2*s**2)
        else:
            return np.exp(-s*dt_kq)*(tmin_kq - .5*s*tmin_kq**2)*mu*D0/2
        
    def KL_simult(smuD):
        mu = smuD[q]**2; D0 = smuD[q+1]**2
        Like = np.zeros(q)
        for jq in xrange(q):
            s = smuD[jq]**2
            if gx is None:
#                Akq0 = akq_mat(s,dt_k)*Lq[jq]/D0
                Akq0 = LA.inv(Kkq_gauss(s,D0/Lq[jq]))
            elif gx == 'sqrt':
                Akq0 = LA.inv(Kkq_sqrt(s,mu,D0/Lq[jq]))
            C = np.eye(Akq0.shape[0]) + sigma**2*Akq0
            Akq = Akq0.dot(LA.inv(C))
            if s > h/np.min(dt_k):
                b_k = mu*(1-np.exp(-s*t_k))/s
            else:
                b_k = mu*t_k 
#            Like[jq] = -.5*np.log(LA.det(Akq0)/LA.det(C)) + 0.5*(pmean_ka[jq,:]-b_k).dot(Akq).dot(pmean_ka[jq,:]-b_k)
            Like[jq] = -.5*np.log(LA.det(Akq0)/LA.det(C)) + 0.5*(pmean_ka[jq,:]-b_k).dot(Akq).dot(pmean_ka[jq,:]-b_k)+\
            + .5*np.trace(Ckqa[jq,:,:].dot(Akq)/Lq[jq])
        if np.isnan(Like).any():
            print smuD**2, Like
        return Like.sum()         
    q = pmean_ka.shape[0]
    K = t_k.shape[0]
    dt_k = np.zeros(K); dt_k[0] = t_k[0]; dt_k[1:] = np.diff(t_k)
    if Lq is None:
        Lq = np.ones(q)
    if sigma is None:
        sigma = 0.
    smuD0 = 10**(-3)*np.ones(q+2)
    step = 10**(-4)*np.ones(q+2)
    tol = h
    smuD = amoeba_vp(KL_simult,smuD0,args=(),a = step,tol_x = tol,tol_f = tol)
    return smuD**2


'''Kullback-Leibler fitting for fixed mutation rate'''

def akq_mat(s,dt_k):
    if s > h/np.min(dt_k):
        a0 =  2*s/(1-np.exp(-2*s*dt_k))
        a0[:-1] += 2*s*np.exp(-2*s*dt_k[1:])/(1-np.exp(-2*s*dt_k[1:]))
        a1 = - 2*s*np.exp(-s*dt_k[1:])/(1-np.exp(-2*s*dt_k[1:])) 
    else:
        a0 =  1/dt_k
        a0[:-1] += (1.- s*dt_k[1:])**2/dt_k[1:]
        a1 = -(1.- s*dt_k[1:])/dt_k[1:]
    return (np.diag(a0) + np.diag(a1,1) + np.diag(a1,-1))
    
def KLfit_simult_mu(Ckqa,pmean_ka,t_k,mu,Lq = None,sigma = None):
    '''Simultaneous KL divergence minimization for several quantiles 
    for a fixed mutation rate''' 
    def Kkq_gauss(s,D0):
        '''Correlation matrix'''
        t_kq = np.tile(t_k,(t_k.shape[0],1))
        dt_kq = np.abs(t_kq - t_kq.T)
        tmin_kq = (t_kq + t_kq.T -dt_kq)/2
        if s > h/np.min(dt_k):
            return np.exp(-s*dt_kq)*(1. - np.exp(-2*s*tmin_kq))*D0/(2*s)
        else:
            return np.exp(-s*dt_kq)*(2*tmin_kq - 2*s*tmin_kq**2)*D0/2
        
    def KL_simult(sD):
        D0 = sD[-1]**2
        Like = np.zeros(q)
        for jq in xrange(q):
            s = sD[jq]**2
#            Akq0 = akq_mat(s,dt_k)*Lq[jq]/D0
            Akq0 = LA.inv(Kkq_gauss(s,D0/Lq[jq]))
            if np.isinf(Akq0).any():
                print sD**2
                print Akq0
            C = np.eye(Akq0.shape[0]) + sigma**2*Akq0
            Akq = Akq0.dot(LA.inv(C))
            if s > h/np.min(dt_k):
                b_k = mu*(1-np.exp(-s*t_k))/s
            else:
                b_k = mu*t_k 
#            Like[jq] = -.5*np.log(LA.det(Akq0)/LA.det(C)) + 0.5*(pmean_ka[jq,:]-b_k).dot(Akq).dot(pmean_ka[jq,:]-b_k)
            Like[jq] = -.5*np.log(LA.det(Akq0)/LA.det(C)) + 0.5*(pmean_ka[jq,:]-b_k).dot(Akq).dot(pmean_ka[jq,:]-b_k)+\
            + .5*np.trace(Ckqa[jq,:,:].dot(Akq)/Lq[jq])
        if np.isnan(Like).any() or np.isinf(Like).any():
            print 'Problem in KLfit_simult_mu\n    sD = ',sD**2,'LogLikelihood = ', Like.sum()
        return Like.sum()      
        
    q = pmean_ka.shape[0]; K = t_k.shape[0]
    dt_k = np.zeros(K); dt_k[0] = t_k[0]; dt_k[1:] = np.diff(t_k)
    if Lq is None:
        Lq = np.ones(q)
    if sigma is None:
        sigma = 0.
    sD0 = 10**(-3)*np.ones(q+1); step = 10**(-4)*np.ones(q+1); tol = h
    sD = amoeba_vp(KL_simult,sD0,args=(),a = step,tol_x = tol,tol_f = tol)
    return sD**2       


def amoeba_vp(func,x0,args = (),Nit = 10**4,a = None,tol_x = 10**(-4),tol_f = 10**(-4),return_f = False):
    '''Home-made realization of multivariate Nelder-Mead minimum search
        
    Input arguments:
    func - function to minimize (function fo a vecor argument of dimension no less than 2) 
    x0 - initial minimum guess
    args - additional arguments for the function
    Nit - maximum number of iterations
    a - edge length of the initial simplx
    tol_x, tol_f - required relative tolerances of argument and function
    return_f - return the function value and the number of iterations
    
    Output arguments:
    position of the minimum
    '''
    
    '''Nelder-Mead parameters'''
    alpha = 1.; gamma = 2.; rho = -.5; sigma = .5
    
    n = x0.shape[0]   
    if a is None:
        a = np.ones(n)
#    a = 1. # edge length of the initial simplex
    xx = np.tile(x0,(n+1,1))
    xx[1:,:] += np.diag(a)
    ff = np.array([func(x,*args) for x in xx])
    
    for j in xrange(Nit):
        xcenter = np.tile(np.mean(xx,axis=0),(n+1,1))
        fmean = np.mean(ff)
        if (np.abs(xx-xcenter) < tol_x*np.abs(xcenter)).all() and (np.abs(ff-fmean) < tol_f*np.abs(fmean)).all():
            break
        '''order'''
        jjsort = np.argsort(ff)
        ff = ff[jjsort]
        xx = xx[jjsort,:]
#        print j,'\n',xx,'\nf = ', ff
        
        '''centroid point'''
        xo = np.mean(xx[:n,:],axis=0)        
        
        '''reflection'''
        xr = xo + alpha*(xo - xx[n,:])
        fr = func(xr,*args)
#        print 'xr,fr = ', xr,fr
        if fr >= ff[0] and fr < ff[-2]:
            xx[-1,:] = xr
            ff[-1] = fr
            continue
        elif fr < ff[0]:
            xe = xo + gamma*(xo - xx[n,:])
            fe = func(xe,*args)
#            print 'xe,fe = ', xe,fe
            if fe < fr:
                xx[-1,:] = xe
                ff[-1] = fe
                continue
            else:
                xx[-1,:] = xr
                ff[-1] = fr
                continue
        else:
            xc = xo + rho*(xo-xx[n,:])
            fc = func(xc,*args)
#            print 'xc,fc = ', xc,fc
            if fc < ff[-1]:
                xx[-1,:] = xc
                ff[-1] = fc
                continue
            else:
                xx = xx[0,:] + sigma*(xx - xx[0,:])
    
    if j == Nit -1:
        print 'WARNING from amoeba_vp:\n    the maximum number of iterations has been reached,\n    max(dx/x) = ',\
        np.max(np.abs((xx-xcenter)/xcenter)),\
        '\n    max(df/f) = ', np.max(np.abs((ff-fmean)/fmean))
    if return_f:
        return xx[0,:],ff[0], j
    else:
        return xx[0,:]
        
if __name__=="__main__":
    '''Studying sampling noise'''
    plt.ioff()
    
    gen_region = 'pol' #'gag' #'pol' #'gp41' #'gp120' #'vif' #'RRE'
    patient_names = ['p1','p2','p3','p5','p6','p8','p9','p11'] #['p1','p2','p5','p6','p9','p11'] 
    # 'p4', 'p7' do not exist
    # 'p10' - weird messages from Patient class
    # p3, p8 - True mask for some time points

    print 'Number of arguments:', len(sys.argv), 'arguments.'
    print 'Argument List:', str(sys.argv)
    
    if len(sys.argv) > 1:
        outdir_name = sys.argv[1]
    else:
        outdir_name = '/ebio/ag-neher/share/users/vpuller/'+\
        'Fabio_data_work/Sampling_noise/KLonly/'
    if not os.path.exists(outdir_name):
        os.makedirs(outdir_name)
    
    if len(sys.argv) > 2:
        q = int(sys.argv[2])
    else:
        q = 7

    tt_all = []; xk_q_all = []
    smuD_KLsim_q = np.zeros((len(patient_names),q+2))
    smuD_KLmu_q = np.zeros((len(patient_names),q+2))
    Lq = np.zeros((len(patient_names),q),dtype = 'int')
    xcut = 0.0; xcut_up = 0.
    div = False
    outliers = True
    for jpat, pat_name in enumerate(patient_names):
        '''Load data and split it into quantiles'''
        print '\n',pat_name
        PAT = Patient.load(pat_name)
        tt = PAT.times()
        freqs = PAT.get_allele_frequency_trajectories(gen_region)
        if np.count_nonzero(freqs.mask) > 0:
            print 'non-zero mask in ' + pat_name + ': removing ' +\
            str(np.count_nonzero(freqs.mask.sum(axis=2).sum(axis=1)>0)) +\
            ' time points out of ' + str(tt.shape[0])  
            tt = tt[np.where(freqs.mask.sum(axis=2).sum(axis=1) == 0)]
            freqs = freqs[np.where(freqs.mask.sum(axis=2).sum(axis=1) == 0)[0],:,:]
        
        tt_all.append(tt); L = freqs.shape[-1]
        jjnuc0 = np.argmax(freqs[0,:4,:],axis=0)
        dt_k = np.zeros(tt.shape[0]); dt_k[0] = tt[0]; dt_k[1:] = np.diff(tt)
        xave = dt_k.dot(freqs[:,jjnuc0,range(jjnuc0.shape[0])])/tt[-1]
        jj2 = np.where((xave <= 1.-xcut)*(xave > xcut_up))[0]
                
        ref = HIVreference(load_alignment=False)
        map_to_ref = PAT.map_to_external_reference(gen_region)
        Squant = ref.get_entropy_quantiles(q)
        xka_q = []
        for jq in xrange(q):
            idx_ref = Squant[jq]['ind']
            idx_PAT = np.array([map_to_ref[i,2] for i,jref in enumerate(map_to_ref[:,0]) 
            if jref in idx_ref and map_to_ref[i,2] in jj2])

            if div:
                x_ka = (1.- freqs[:,jjnuc0[idx_PAT],idx_PAT])*freqs[:,jjnuc0[idx_PAT],idx_PAT]
            else:
                x_ka = 1.- freqs[:,jjnuc0[idx_PAT],idx_PAT]
            xka_q.append(x_ka)
        
        '''Remove outliers from the data'''
        if outliers:
            '''Removing outliers using a maximum frequency cutoff'''
            out = []; xka_q_new = []
            for jq, x_ka0 in enumerate(xka_q): 
                out = np.where(x_ka0.data > .5)[1]
                nonout0 = range(x_ka0.shape[1]); nonout = [j for j in nonout0 if j not in out]
                xka_q_new.append(xka_q[jq][:,nonout])
            xka_q = list(xka_q_new)

        '''Analyze data'''
        xk_q = np.zeros((q,tt.shape[0]))
        Ckq_q = np.zeros((q,tt.shape[0],tt.shape[0]))
        for jq, x_ka in enumerate(xka_q): 
            Lq[jpat,jq] = x_ka.shape[1]
            xk_q[jq,:] = x_ka.mean(axis=1)
            Ckq_q[jq,:,:] = Covariance(x_ka)


        '''Simultaneous KL fit of fitness coefficients and mutation rates'''
        smuD_KLsim_q[jpat,:] = KLfit_simult_new_sigma(Ckq_q,xk_q,tt) 
        
        '''Mutation rates from linear fitting of the upper quantile'''
        smuD_KLmu_q[jpat,q] = fit_upper(xka_q[q-1],tt)
        
        '''KL fitting fitness coefficients for the given mutation rate'''
        ii_sD = range(q+2); ii_sD.remove(q)
        smuD_KLmu_q[jpat,ii_sD] = KLfit_simult_mu(Ckq_q,xk_q,tt,smuD_KLmu_q[jpat,q]) 
        xk_q_all.append(xk_q)
     
    '''Saving fitness coefficients and mutation rates'''
    header = ['s' + str(jq+1) for jq in range(q)]
    header.extend(['mu','D'])
    np.savetxt(outdir_name + 'smuD_KL.txt',smuD_KLsim_q,header = '\t\t\t'.join(header))
    np.savetxt(outdir_name + 'smuD_KLmu.txt',smuD_KLmu_q,header = '\t\t\t'.join(header))
    
    
    '''Bootstrapping'''
    Nboot = 10**5
    smuD_boot = np.zeros((Nboot,q+2))
    smuD_boot_mu = np.zeros((Nboot,q+2))
    for jboot in xrange(Nboot):
        smuD_boot[jboot,:] = smuD_KLsim_q[np.random.randint(0,len(patient_names),len(patient_names)),:].mean(axis=0)
        smuD_boot_mu[jboot,:] = smuD_KLmu_q[np.random.randint(0,len(patient_names),len(patient_names)),:].mean(axis=0)
    
    smuD_boot_mean = smuD_boot.mean(axis=0)
    smuD_boot_sigma = np.sqrt((smuD_boot**2).mean(axis=0) - smuD_boot.mean(axis=0)**2)
    smuD_boot_mu_mean = smuD_boot_mu.mean(axis=0)
    smuD_boot_mu_sigma = np.sqrt((smuD_boot_mu**2).mean(axis=0) - smuD_boot_mu.mean(axis=0)**2)
    
    np.savetxt(outdir_name + 'smuD_KL_boot.txt',np.array([smuD_boot_mean, smuD_boot_sigma]),header = '\t\t\t'.join(header))
    np.savetxt(outdir_name + 'smuD_KLmu_boot.txt',np.array([smuD_boot_mu_mean, smuD_boot_mu_sigma]),header = '\t\t\t'.join(header))
    
    '''Plots'''
#    plt.figure(10,figsize=(20,6)); plt.clf()
#    for jpat, tt in enumerate(tt_all):
#        plt.scatter(tt,xk_q_all[jpat][jq,:],color = cols[jpat])
#        plt.plot(tt,smuD_KLmu_q[jpat,q]*tt,'-',color = cols[jpat])
#    plt.xlabel('t')
#    plt.ylabel('xk')
#    plt.legend(patient_names,loc=0)
#    plt.title('quantile ' + str(jq+1))
#    plt.savefig(outdir_name + 'upper_quant_linear.pdf')
#    plt.close(10)
    

#    data_smu = [smuD_KLsim_q,smuD_KLmu_q]
#    titles = ['KL','KL, mu']
#    ldata = len(data_smu)
#    plt.figure(30,figsize = (8*ldata,18)); plt.clf()
#    for jdata, smu in enumerate(data_smu):
#        plt.subplot(3,ldata,jdata+1)
#        plt.semilogy(range(1,q+1),smu[:,:q].T)
#        plt.xlabel('quantile',fontsize=20)
#        plt.ylabel('s [1/day]',fontsize=20)
#        plt.legend(patient_names,loc=0); plt.ylim([10**(-5),10])
#        plt.title(titles[jdata])
#        
#        plt.subplot(3,ldata,jdata+ldata+1)
#        plt.semilogy(smu[:,q],':o')
#        plt.xticks(np.arange(len(patient_names)),patient_names)
#        plt.ylabel('mu, [1/day]',fontsize=20)
#        
#        plt.subplot(3,ldata,jdata+2*ldata+1)
#        plt.semilogy(smu[:,q+1],':o')
#        plt.xticks(np.arange(len(patient_names)),patient_names)
#        plt.ylabel('D, [1/day]',fontsize=20)
#    plt.savefig(outdir_name + 'smu.pdf')
#    plt.close(30)
#    
#
#    data_mean = np.array([smu.mean(axis=0) for smu in data_smu])
#    data_sigma = np.array([np.sqrt((smu**2).mean(axis=0) - smu.mean(axis=0)**2) for smu in data_smu])    
#    plt.figure(40,figsize = (30,12)); plt.clf() 
#    plt.subplot(2,3,1)
#    for jdata, smu in enumerate(data_smu):
#        plt.errorbar(range(1,q+1),np.log10(data_mean[jdata,:q]),yerr = data_sigma[jdata,:q]/data_mean[jdata,:q],fmt = '--o')
#    plt.ylim((-5,0)); plt.xlim([.5,q+.5])
#    plt.xlabel('Entropy quantile',fontsize = 20); plt.ylabel('s [1/days]',fontsize = 20)
#    plt.legend(titles, loc = 0,fontsize = 20)
#    
#    plt.subplot(2,3,2); plt.plot()
#    plt.errorbar(range(len(data_smu)),data_mean[:,q],yerr = data_sigma[:,q],fmt = '--o')
#    plt.xticks(np.arange(len(data_smu)),titles); plt.xlim([-.5,len(data_smu)-.5])
#    plt.xlabel('Method',fontsize=20); plt.ylabel('mu [1/day]',fontsize=20)
#
#    plt.subplot(2,3,3); plt.plot()
#    plt.errorbar(range(len(data_smu)),data_mean[:,q+1],yerr = data_sigma[:,q+1],fmt = '--o')
#    plt.xticks(np.arange(len(data_smu)),titles); plt.xlim([-.5,len(data_smu)-.5])
#    plt.xlabel('Method',fontsize=20); plt.ylabel('D [1/day]',fontsize=20)
#    
#    
#    plt.subplot(2,3,4)
#    plt.errorbar(range(1,q+1),np.log10(smuD_boot_mean[:q]),yerr = smuD_boot_sigma[:q]/smuD_boot_mean[:q],fmt = '--o')
#    plt.errorbar(range(1,q+1),np.log10(smuD_boot_mu_mean[:q]),yerr = smuD_boot_mu_sigma[:q]/smuD_boot_mu_mean[:q],fmt = '--o')
#    plt.ylim((-5,0)); plt.xlim([.5,q+.5])
#    plt.xlabel('Entropy quantile',fontsize = 20); plt.ylabel('s [1/days]',fontsize = 20)
#    plt.legend(titles, loc = 0,fontsize = 20)
#    
#    plt.subplot(2,3,5); plt.plot()
#    plt.errorbar(range(len(data_smu)),[smuD_boot_mean[q],smuD_boot_mu_mean[q]],\
#    yerr = [smuD_boot_sigma[q],smuD_boot_mu_sigma[q]],fmt = '--o')
#    plt.xticks(np.arange(len(data_smu)),titles); plt.xlim([-.5,len(data_smu)-.5])
#    plt.xlabel('Method',fontsize=20); plt.ylabel('mu [1/day]',fontsize=20)
#
#    plt.subplot(2,3,6); plt.plot()
#    plt.errorbar(range(len(data_smu)),[smuD_boot_mean[q+1],smuD_boot_mu_mean[q+1]],\
#    yerr = [smuD_boot_sigma[q+1],smuD_boot_mu_sigma[q+1]],fmt = '--o')
#    plt.xticks(np.arange(len(data_smu)),titles); plt.xlim([-.5,len(data_smu)-.5])
#    plt.xlabel('Method',fontsize=20); plt.ylabel('D [1/day]',fontsize=20)
#    
#    plt.savefig(outdir_name + 'smu_mean.pdf'); plt.close(40)
#        
#        
#    xlab = ['q' + str(jq+1) for jq in xrange(q)]; xlab.extend(['mu','D'])
#    plt.figure(50,figsize=(6*(q+2),12)); plt.clf()
#    for jq in xrange(q+2):
#        plt.subplot(2,q+2,jq+1)
#        plt.hist(smuD_boot[:,jq]); plt.xlabel(xlab[jq]); plt.ylabel('KL')
#
#        plt.subplot(2,q+2,q+jq+3)
#        plt.hist(smuD_boot_mu[:,jq]); plt.xlabel(xlab[jq]); plt.ylabel('KL, mu')
#    plt.savefig(outdir_name + 'boot_hist.pdf')
#    
#    

#    plt.figure(20,figsize=(20,6*len(tt_all))); plt.clf()
#    for jpat, tt in enumerate(tt_all):
#        plt.subplot(len(tt_all),1,jpat+1)
#        for jq in xrange(q):
#            plt.scatter(tt,xk_q_all[jpat][jq,:],color = cols_Fabio[jq])
#            plt.plot(tt,curve_smu(smuD_KLsim_q[jpat,[jq,q]],tt),'-',color = cols_Fabio[jq])
#            plt.plot(tt,curve_smu(smuD_KLmu_q[jpat,[jq,q]],tt),'--',color = cols_Fabio[jq])
#        plt.xlabel('t'); plt.ylabel('xk')
#        plt.legend(titles,loc = 0)
#        plt.title(patient_names[jpat])
#    plt.savefig(outdir_name + 'KL_fit_bypat.pdf'); plt.close(20)
    
