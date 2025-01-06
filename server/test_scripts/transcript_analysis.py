from controllers.transcript_controller import TranscriptController

yt_url = 'https://www.youtube.com/watch?v=bDf4OvBolAQ'

tc = TranscriptController()
res = tc.store_transcript(yt_url)

transcript_id = res['transcript_id']

analysis_res = tc.analyze_transcript(transcript_id)