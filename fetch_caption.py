from youtube_transcript_api import YouTubeTranscriptApi

#
def caption(link):
    # transcript_list = YouTubeTranscriptApi()
    ytt_api = YouTubeTranscriptApi()
    # print(ytt_api.list_transcripts(link).find_transcript(['hi','en']))
    # print(ytt_api.list_transcripts(link))
    # fetched_data = ytt_api.fetch(video_id="sD10Uf-Ksn8")
    # print(ytt_api.get_transcript(video_id=link, languages = ['hi','en']))
    try:
        hindi_transcript = ytt_api.fetch(video_id=link,languages = ['hi','en'])
        return hindi_transcript
    except Exception as e:
        print(f"Transcript not found or error: {e}")
        return None
    #return( ' '.join([entry['text'] for entry in hindi_transcript]) ) 

# print(YouTubeTranscriptApi().fetch("T2Glm9_-rJQ", languages=['hi', 'en'], preserve_formatting=True))

# result = caption(link="r9q4AQ_dDzg")
# for entry in result:
#     print(entry)
#https://www.youtube.com/watch?v=r9q4AQ_dDzghttps://www.youtube.com/watch?v=r9q4AQ_dDzg

def get_captions_up_to_hour(captions, input_minutes):
    """
    Returns concatenated text from captions starting from beginning until specified hour.
    
    Args:
        captions (list): List of caption dictionaries with 'text', 'start' (minutes), and 'duration'
        input_hours (float): Target hour to collect captions up to (e.g., 1.5 for 1 hour 30 minutes)
    
    Returns:
        str: Concatenated text from selected captions
    """
    # Convert hours to minutes (since start times are in minutes)
    target_minutes = input_minutes*60
    
    # Sort captions by their start time to ensure chronological order
    #sorted_captions = sorted(captions, key=lambda x: x.get('start', 0))
    
    selected_text = []
    for caption in captions:
        if caption.start <= target_minutes:
            selected_text.append(caption.text)
        else:
            break  # Stop checking once we pass target time
    
    return ' '.join(selected_text)

# Example usage: UuSN7_Vc3-U.  JBX1jc09zsg

#result = caption(link="NPABYNtgySY")
#print(result)   
# print(get_captions_up_to_hour(caption(link="r9q4AQ_dDzg"), input_minutes=70))

# with open('Blogs data/blog_final copy.txt', 'w') as file:
#     file.write(result)
#     print("Writing Done")

#result = get_captions_up_to_hour(caption(link="GAmQe3nWhvc"), 2)

#https://www.youtube.com/watch?v=ul0QsodYct4&pp=ygUSYWkgYWdlbnRzIHR1dG9yaWFs
# def write_blog(text):
#     with open('transcript.txt', 'w') as file:
#     # Write content to the file
#         file.write(text)
#         print("Writing Done")

# write_blog(text=result)
# print(caption(link="hOI0i4IY11M"))
# print(get_captions_up_to_hour(caption(link="hOI0i4IY11M"), input_minutes=40))