"""Conservative adaptive stationary-background suppression for AuraForest."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import torch

@dataclass
class NoiseRobustnessResult:
    enabled: bool
    applied: bool
    input_rms: float
    output_rms: float
    estimated_noise_rms: float
    estimated_snr_db: float | None
    attenuation_db: float
    reason: str
    def to_dict(self):
        return {
            "enabled": bool(self.enabled), "applied": bool(self.applied),
            "input_rms": float(self.input_rms), "output_rms": float(self.output_rms),
            "estimated_noise_rms": float(self.estimated_noise_rms),
            "estimated_snr_db": None if self.estimated_snr_db is None else float(self.estimated_snr_db),
            "attenuation_db": float(self.attenuation_db), "reason": str(self.reason),
        }

class NoiseRobustnessEngine:
    """Adaptive spectral subtraction with a gain floor to protect target events."""
    def __init__(self, enabled=True, n_fft=1024, hop_length=256,
                 noise_percentile=20.0, subtraction_strength=0.85,
                 gain_floor=0.25, activation_noise_ratio=0.10,
                 min_rms=0.0015):
        self.enabled=bool(enabled); self.n_fft=int(n_fft); self.hop_length=int(hop_length)
        self.noise_percentile=float(noise_percentile); self.subtraction_strength=float(subtraction_strength)
        self.gain_floor=float(gain_floor); self.activation_noise_ratio=float(activation_noise_ratio)
        self.min_rms=float(min_rms)
        self._window=torch.hann_window(self.n_fft)
    @staticmethod
    def _rms(x):
        x=np.asarray(x,dtype=np.float32).reshape(-1)
        return float(np.sqrt(np.mean(np.square(x),dtype=np.float64))) if x.size else 0.0
    @staticmethod
    def _snr_db(signal_rms, noise_rms):
        if signal_rms<=0 or noise_rms<=0: return None
        return float(20*math.log10(max(signal_rms/noise_rms,1e-12)))
    def _identity(self,x,reason):
        rms=self._rms(x)
        return x.copy(), NoiseRobustnessResult(self.enabled,False,rms,rms,0.0,None,0.0,reason)
    def process(self,waveform,sample_rate=16000):
        x=np.asarray(waveform,dtype=np.float32).reshape(-1)
        if x.size==0: return self._identity(x,"empty_audio")
        if not self.enabled: return self._identity(x,"disabled")
        input_rms=self._rms(x)
        if input_rms<self.min_rms: return self._identity(x,"signal_below_activity_threshold")
        if x.size<max(self.n_fft*3,int(sample_rate*.25)):
            return self._identity(x,"audio_too_short_for_noise_estimation")
        t=torch.from_numpy(x); w=self._window.to(dtype=t.dtype)
        with torch.no_grad():
            spec=torch.stft(t,n_fft=self.n_fft,hop_length=self.hop_length,
                            win_length=self.n_fft,window=w,center=True,return_complex=True)
            mag=spec.abs()
            floor=torch.quantile(mag,self.noise_percentile/100.0,dim=-1,keepdim=True)
            noise_mag=torch.minimum(mag,floor)
            noise_spec=noise_mag*torch.exp(1j*torch.angle(spec))
            nw=torch.istft(noise_spec,n_fft=self.n_fft,hop_length=self.hop_length,
                           win_length=self.n_fft,window=w,center=True,length=x.size)
            noise_rms=self._rms(nw.numpy())
            ratio=noise_rms/max(input_rms,1e-12)
            if ratio<self.activation_noise_ratio:
                return x.copy(), NoiseRobustnessResult(
                    True,False,input_rms,input_rms,noise_rms,self._snr_db(input_rms,noise_rms),
                    0.0,"stationary_noise_below_activation_threshold")
            residual=torch.relu(mag-self.subtraction_strength*floor)
            gain=torch.clamp(residual/mag.clamp_min(1e-8),min=self.gain_floor,max=1.0)
            clean=torch.istft(spec*gain,n_fft=self.n_fft,hop_length=self.hop_length,
                              win_length=self.n_fft,window=w,center=True,length=x.size)
        y=clean.numpy().astype(np.float32,copy=False)
        peak=float(np.max(np.abs(y))) if y.size else 0.0
        if peak>1.0: y=y/peak
        out_rms=self._rms(y)
        att=float(20*math.log10(max(out_rms,1e-12)/max(input_rms,1e-12)))
        return y, NoiseRobustnessResult(
            True,True,input_rms,out_rms,noise_rms,self._snr_db(input_rms,noise_rms),
            att,"stationary_background_suppressed")
    def get_config(self):
        return {"enabled":self.enabled,"n_fft":self.n_fft,"hop_length":self.hop_length,
                "noise_percentile":self.noise_percentile,"subtraction_strength":self.subtraction_strength,
                "gain_floor":self.gain_floor,"activation_noise_ratio":self.activation_noise_ratio,
                "min_rms":self.min_rms}
