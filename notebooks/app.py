import streamlit as st
import torch
from io import BytesIO
#from your_pytorch_model_module import classify_audio  # Ensure this is your PyTorch model function
from AudioModel import * # CNNNetwork()
from AudioDataset import * # AudioEmotionDataset()

from IPython.display import Audio
from matplotlib.patches import Rectangle
from torchaudio.utils import download_asset

# audio recorder project
# https://pypi.org/project/audio-recorder-streamlit/
from audio_recorder_streamlit import audio_recorder


# TODO: return the figure from the following funtions for streamlit plotting purposes
# https://pytorch.org/audio/main/tutorials/audio_feature_extractions_tutorial.html#sphx-glr-tutorials-audio-feature-extractions-tutorial-py
def plot_waveform(waveform, sr, title="Waveform", ax=None):
    waveform = waveform.numpy()

    num_channels, num_frames = waveform.shape
    time_axis = torch.arange(0, num_frames) / sr

    if ax is None: 
        fig, ax = plt.subplots(num_channels, 1)
    ax.plot(time_axis, waveform[0], linewidth=1)
    ax.grid(True)
    ax.set_xlim([0, time_axis[-1]])
    ax.set_title(title)

    st.pyplot(fig)


def plot_spectrogram(specgram, title=None, ylabel="freq_bin", ax=None):
    if ax is None:
        fig, ax = plt.subplots(1, 1)
    if title is not None:
        ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.imshow(librosa.power_to_db(specgram), origin="lower", aspect="auto", interpolation="nearest")

    st.pyplot(fig)


def plot_fbank(fbank, title=None):
    fig, axs = plt.subplots(1, 1)
    axs.set_title(title or "Filter bank")
    axs.imshow(fbank, aspect="auto")
    axs.set_ylabel("frequency bin")
    axs.set_xlabel("mel bin")

    st.pyplot(fig)


# streamlit run app.py --server.enableXsrfProtection false
# this prevents the error: AxiosError: Request failed with status code 403
def main():
    st.title('Audio Emotion Classifier')
    
    # Upload audio file or record audio
    audio_file = st.file_uploader("Upload an audio file", type=['wav'])
    # record = st.checkbox("Or record audio")

    # if record:
    #     audio_data = st.audio_recorder("Record your audio", type="wav", time_limit=10)
    #     if audio_data:
    #         audio_bytes = audio_data.read()
    #         audio_file = BytesIO(audio_bytes)
    audio_bytes = audio_recorder()
    if audio_bytes:
        # playback audio
        audio_file = BytesIO(audio_bytes)

    if audio_file is not None:
        # Assuming classify_audio expects a file-like object
        #label = classify_audio(audio_file)
        #st.write(f"The predicted category is: {label}")

        st.audio(audio_bytes, format="audio/wav")

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        signal, sr = torchaudio.load(audio_file)
        signal = signal.to(device)

        hyperparameters = dict(
        target_sample_rate=16000,
        num_samples=22050, 
        n_fft=1024, 
        hop_length=512, 
        n_mels=64, 
        sr = sr
        )

        # process the signal so it's in desired format
        signal = processing_pipeline(signal, hyperparameters)

        waveform_signal = signal # Save the waveform signal for later
        print(signal.shape)

        plot_waveform(signal, sr, title="Waveform")

        mel_spectrogram = torchaudio.transforms.MelSpectrogram(
            sample_rate=hyperparameters['target_sample_rate'],
            n_fft=hyperparameters['n_fft'],
            hop_length=hyperparameters['hop_length'],
            n_mels=hyperparameters['n_mels']
        )

        # apply transformation to the signal
        signal = mel_spectrogram(signal)

        # save the mel_spectrogram so that we can show the
        # user what it looks like

        # turn the spectrogram into 2 dimensional image for matplotlib 
        spectrogram_output = signal.squeeze() 

        print(spectrogram_output.shape)
        plot_spectrogram(spectrogram_output, title="Mel Spectrogram")

        # convert to decibels (kinda)
        signal = torch.log(signal + 0.00001)

        # add a channel dimension so that model thinks it's a batch
        signal = signal.unsqueeze(0) 

        # Load the model
        model = CNNNetwork().to(device)
        model.load_state_dict(torch.load('feedforwardnet.pth', map_location=torch.device("cpu")))
        model.eval()
        # Make a prediction

        emotion_map = ['HAP', 'NEU', 'ANG', 'FEA', 'DIS', 'SAD']

        with torch.no_grad():
            predictions = model(signal)
            st.write('Predictions:', predictions)
            predicted_index = predictions.argmax(1).item()
            st.write(f'Predicted class index: {emotion_map[predicted_index]}')

            predictions = predictions.squeeze().numpy()
            #st.write(predictions)

            df = pd.DataFrame({'emotion': emotion_map, 'probability': predictions})
            st.header('Predicted Emotion Probabilities')
            st.bar_chart(data=df, x='emotion', y='probability', use_container_width=True)


    

if __name__ == "__main__":
    main()