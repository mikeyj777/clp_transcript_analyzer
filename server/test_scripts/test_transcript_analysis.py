import os
import sys
import csv 
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers.transcript_controller import TranscriptController

vids_df = pd.read_csv('data/clp_vids.csv')

fieldnames = ['analysis_id', 'transcript_id', 'yt_url']
completed_analyses = pd.DataFrame(columns=fieldnames)
latest_analyses = []
transcript_id = 0
header_written = False

try:
  completed_analyses = pd.read_csv('data/completed_analyses.csv')
  transcript_id = completed_analyses['transcript_id'].max() + 1
  header_written = True
except Exception as e:
  print(e)

def get_and_process_transcript(yt_url):
  global transcript_id
  global latest_analyses
  tc = TranscriptController()
  res = tc.get_transcript(yt_url)
  if not res:
    return
  transcript = tc.transcript
  analysis_res = tc.analyze_transcript(transcript, transcript_id)
  if analysis_res[1] != 200:
    return
  latest_analyses.append({'analysis_id': analysis_res['analysis_id'], 'transcript_id': transcript_id, 'yt_url': yt_url})
  transcript_id += 1
  try:
    with open('data/completed_analyses.csv', 'a', newline='') as csvfile:
      writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
      if not header_written:
        writer.writeheader()
        header_written = True
      writer.writerows(latest_analyses)
    latest_analyses = []
  except Exception as e:
    print(e)

for i in range(len(vids_df)):
  vid = vids_df.iloc[i]
  yt_url = vid['url']
  if yt_url in completed_analyses['yt_url'].values:
    continue
  get_and_process_transcript(yt_url)
  if (i + 1) % 5 == 0:
    print(f'Processed {i + 1} videos')

