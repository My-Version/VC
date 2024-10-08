'''
Copied from espnet: https://github.com/espnet/espnet/blob/master/espnet/transform/spectrogram.py
'''
import librosa
import numpy as np
import resampy
import soundfile as sf


def load_wav(wav_path, sr=24000):
    # wav, fs = librosa.load(wav_path, sr=sr)
    wav, fs = sf.read(wav_path)
    if fs != sr:
        wav = resampy.resample(wav, fs, sr, axis=0)
        fs = sr
    # assert fs == sr, f"input audio sample rate must be {sr}Hz. Got {fs}"
    peak = np.abs(wav).max()
    if peak > 1.0:
        wav /= peak
    return wav, fs


# Extract Log-Scaled A-Weighting Loudness from Audio. Added by Xu Li.
def AWeightingLoudness(x, sr, n_fft, n_shift, win_length=None, window='hann', center=True, pad_mode='reflect'):
    assert x.ndim == 1, 'The audio has %d channels, but so far we only support single-channel audios.' %(x.ndim)
    # [Freq, Time]
    mag_stft = np.abs(stft(x, n_fft, n_shift, win_length, window, center, pad_mode).T)

    freq_axis = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    perceptual_stft = librosa.perceptual_weighting(mag_stft**2, freq_axis, ref=1)
    perceptual_loudness = np.log10(np.mean(np.power(10, perceptual_stft/10), axis=0)+1e-5)

    return perceptual_loudness


def extract_voiced_area(wav_path, n_fft=2048, hop_size=480, win_length=2048, window='hann', center=True, pad_mode='reflect', hi_freq=1000, energy_thres=0.5):
    x, sr = load_wav(wav_path)
    assert x.ndim == 1, 'The audio has %d channels, but so far we only support single-channel audios.' %(x.ndim)
    # [Freq, Time]
    mag_stft = np.abs(stft(x, n_fft, hop_size, win_length, window, center, pad_mode).T)
    freq_axis = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    filtered_mag_stft = mag_stft[freq_axis <= hi_freq]
    loudness = np.log10(np.mean(np.power(10, filtered_mag_stft/10), axis=0)+1e-5)
    
    return loudness >= energy_thres


def stft(
    x, n_fft, n_shift, win_length=None, window="hann", center=True, pad_mode="reflect"
):
    # x: [Time, Channel]
    if x.ndim == 1:
        single_channel = True
        # x: [Time] -> [Time, Channel]
        x = x[:, None]
    else:
        single_channel = False
    x = x.astype(np.float32)

    # FIXME(kamo): librosa.stft can't use multi-channel?
    # x: [Time, Channel, Freq]
    x = np.stack(
        [
            librosa.stft(
                x[:, ch],
                n_fft=n_fft,
                hop_length=n_shift,
                win_length=win_length,
                window=window,
                center=center,
                pad_mode=pad_mode,
            ).T
            for ch in range(x.shape[1])
        ],
        axis=1,
    )

    if single_channel:
        # x: [Time, Channel, Freq] -> [Time, Freq]
        x = x[:, 0]
    return x


def istft(x, n_shift, win_length=None, window="hann", center=True):
    # x: [Time, Channel, Freq]
    if x.ndim == 2:
        single_channel = True
        # x: [Time, Freq] -> [Time, Channel, Freq]
        x = x[:, None, :]
    else:
        single_channel = False

    # x: [Time, Channel]
    x = np.stack(
        [
            librosa.istft(
                x[:, ch].T,  # [Time, Freq] -> [Freq, Time]
                hop_length=n_shift,
                win_length=win_length,
                window=window,
                center=center,
            )
            for ch in range(x.shape[1])
        ],
        axis=1,
    )

    if single_channel:
        # x: [Time, Channel] -> [Time]
        x = x[:, 0]
    return x


def stft2logmelspectrogram(x_stft, fs, n_mels, n_fft, fmin=None, fmax=None, eps=1e-10):
    # x_stft: (Time, Channel, Freq) or (Time, Freq)
    fmin = 0 if fmin is None else fmin
    fmax = fs / 2 if fmax is None else fmax

    # spc: (Time, Channel, Freq) or (Time, Freq)
    spc = np.abs(x_stft)
    # mel_basis: (Mel_freq, Freq)
    mel_basis = librosa.filters.mel(sr=fs, n_fft=n_fft, n_mels=n_mels, fmin=fmin, fmax=fmax)
    # lmspc: (Time, Channel, Mel_freq) or (Time, Mel_freq)
    lmspc = np.log10(np.maximum(eps, np.dot(spc, mel_basis.T)))

    return lmspc


def spectrogram(x, n_fft, n_shift, win_length=None, window="hann"):
    # x: (Time, Channel) -> spc: (Time, Channel, Freq)
    spc = np.abs(stft(x, n_fft, n_shift, win_length, window=window))
    return spc


def logmelspectrogram(
    x,
    fs,
    n_mels,
    n_fft,
    n_shift,
    win_length=None,
    window="hann",
    fmin=None,
    fmax=None,
    eps=1e-10,
    pad_mode="reflect",
):
    # stft: (Time, Channel, Freq) or (Time, Freq)
    x_stft = stft(
        x,
        n_fft=n_fft,
        n_shift=n_shift,
        win_length=win_length,
        window=window,
        pad_mode=pad_mode,
    )

    return stft2logmelspectrogram(
        x_stft, fs=fs, n_mels=n_mels, n_fft=n_fft, fmin=fmin, fmax=fmax, eps=eps
    )


class Spectrogram(object):
    def __init__(self, n_fft, n_shift, win_length=None, window="hann"):
        self.n_fft = n_fft
        self.n_shift = n_shift
        self.win_length = win_length
        self.window = window

    def __repr__(self):
        return (
            "{name}(n_fft={n_fft}, n_shift={n_shift}, "
            "win_length={win_length}, window={window})".format(
                name=self.__class__.__name__,
                n_fft=self.n_fft,
                n_shift=self.n_shift,
                win_length=self.win_length,
                window=self.window,
            )
        )

    def __call__(self, x):
        return spectrogram(
            x,
            n_fft=self.n_fft,
            n_shift=self.n_shift,
            win_length=self.win_length,
            window=self.window,
        )


class LogMelSpectrogram(object):
    def __init__(
        self,
        fs,
        n_mels,
        n_fft,
        n_shift,
        win_length=None,
        window="hann",
        fmin=None,
        fmax=None,
        eps=1e-10,
    ):
        self.fs = fs
        self.n_mels = n_mels
        self.n_fft = n_fft
        self.n_shift = n_shift
        self.win_length = win_length
        self.window = window
        self.fmin = fmin
        self.fmax = fmax
        self.eps = eps

    def __repr__(self):
        return (
            "{name}(fs={fs}, n_mels={n_mels}, n_fft={n_fft}, "
            "n_shift={n_shift}, win_length={win_length}, window={window}, "
            "fmin={fmin}, fmax={fmax}, eps={eps}))".format(
                name=self.__class__.__name__,
                fs=self.fs,
                n_mels=self.n_mels,
                n_fft=self.n_fft,
                n_shift=self.n_shift,
                win_length=self.win_length,
                window=self.window,
                fmin=self.fmin,
                fmax=self.fmax,
                eps=self.eps,
            )
        )

    def __call__(self, x):
        return logmelspectrogram(
            x,
            fs=self.fs,
            n_mels=self.n_mels,
            n_fft=self.n_fft,
            n_shift=self.n_shift,
            win_length=self.win_length,
            window=self.window,
        )


class Stft2LogMelSpectrogram(object):
    def __init__(self, fs, n_mels, n_fft, fmin=None, fmax=None, eps=1e-10):
        self.fs = fs
        self.n_mels = n_mels
        self.n_fft = n_fft
        self.fmin = fmin
        self.fmax = fmax
        self.eps = eps

    def __repr__(self):
        return (
            "{name}(fs={fs}, n_mels={n_mels}, n_fft={n_fft}, "
            "fmin={fmin}, fmax={fmax}, eps={eps}))".format(
                name=self.__class__.__name__,
                fs=self.fs,
                n_mels=self.n_mels,
                n_fft=self.n_fft,
                fmin=self.fmin,
                fmax=self.fmax,
                eps=self.eps,
            )
        )

    def __call__(self, x):
        return stft2logmelspectrogram(
            x,
            fs=self.fs,
            n_mels=self.n_mels,
            n_fft=self.n_fft,
            fmin=self.fmin,
            fmax=self.fmax,
        )


class Stft(object):
    def __init__(
        self,
        n_fft,
        n_shift,
        win_length=None,
        window="hann",
        center=True,
        pad_mode="reflect",
    ):
        self.n_fft = n_fft
        self.n_shift = n_shift
        self.win_length = win_length
        self.window = window
        self.center = center
        self.pad_mode = pad_mode

    def __repr__(self):
        return (
            "{name}(n_fft={n_fft}, n_shift={n_shift}, "
            "win_length={win_length}, window={window},"
            "center={center}, pad_mode={pad_mode})".format(
                name=self.__class__.__name__,
                n_fft=self.n_fft,
                n_shift=self.n_shift,
                win_length=self.win_length,
                window=self.window,
                center=self.center,
                pad_mode=self.pad_mode,
            )
        )

    def __call__(self, x):
        return stft(
            x,
            self.n_fft,
            self.n_shift,
            win_length=self.win_length,
            window=self.window,
            center=self.center,
            pad_mode=self.pad_mode,
        )


class IStft(object):
    def __init__(self, n_shift, win_length=None, window="hann", center=True):
        self.n_shift = n_shift
        self.win_length = win_length
        self.window = window
        self.center = center

    def __repr__(self):
        return (
            "{name}(n_shift={n_shift}, "
            "win_length={win_length}, window={window},"
            "center={center})".format(
                name=self.__class__.__name__,
                n_shift=self.n_shift,
                win_length=self.win_length,
                window=self.window,
                center=self.center,
            )
        )

    def __call__(self, x):
        return istft(
            x,
            self.n_shift,
            win_length=self.win_length,
            window=self.window,
            center=self.center,
        )
