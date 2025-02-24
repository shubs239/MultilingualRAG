from youtube_transcript_api import YouTubeTranscriptApi
#
def caption(link):
    transcript_list = YouTubeTranscriptApi.list_transcripts(link)#add youtube link
    # Get the Hindi transcript, which is auto-generated
    hindi_transcript = transcript_list.find_transcript(['hi']).fetch() 
    #print(hindi_transcript)

    return( ' '.join([entry['text'] for entry in hindi_transcript]) ) 
