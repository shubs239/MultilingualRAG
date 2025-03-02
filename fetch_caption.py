from youtube_transcript_api import YouTubeTranscriptApi
#
def caption(link):
    transcript_list = YouTubeTranscriptApi.list_transcripts(link)#add youtube link
    # Get the Hindi transcript, which is auto-generated
    hindi_transcript = transcript_list.find_transcript(['hi']).fetch() 
    return (hindi_transcript)

    #return( ' '.join([entry['text'] for entry in hindi_transcript]) ) 

#caption(link="GAmQe3nWhvc")




def get_captions_up_to_hour(captions, input_hours):
    """
    Returns concatenated text from captions starting from beginning until specified hour.
    
    Args:
        captions (list): List of caption dictionaries with 'text', 'start' (minutes), and 'duration'
        input_hours (float): Target hour to collect captions up to (e.g., 1.5 for 1 hour 30 minutes)
    
    Returns:
        str: Concatenated text from selected captions
    """
    # Convert hours to minutes (since start times are in minutes)
    target_minutes = input_hours * 60
    
    # Sort captions by their start time to ensure chronological order
    sorted_captions = sorted(captions, key=lambda x: x['start'])
    
    selected_text = []
    for caption in sorted_captions:
        if caption['start'] <= target_minutes:
            selected_text.append(caption['text'])
        else:
            break  # Stop checking once we pass target time
    
    return ' '.join(selected_text)


#result = get_captions_up_to_hour(caption(link="GAmQe3nWhvc"), 2)

#
# def write_blog(text):
#     with open('transcript.txt', 'w') as file:
#     # Write content to the file
#         file.write(text)
#         print("Writing Done")

# write_blog(text=result)
#print(caption(link="WLCqaUqvOP4"))