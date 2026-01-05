import datetime
import pytz

def get_current_time():

    """
    Returns the current time and date in Central Standard Time.
    This function is used by the AI Agent to provide real-time 
    context to the user.
    """

    # Define the timezone for CST
    cst_timezone = pytz.timezone('US/Central')
    
    # Get the current time in CST
    now = datetime.datetime.now(cst_timezone)
    
    # Format: "03:32 PM CST on December 29, 2025"
    return now.strftime("%I:%M %p %Z on %B %d, %Y")



def get_iso_timestamp():
    """Returns a UTC ISO-8601 timestamp for the Mendix payload."""
    return datetime.datetime.now(pytz.utc).isoformat()

