import streamlit.components.v1 as components
import os

def timer_component(end_time_iso):
    # Get the directory of the current file
    dir_path = os.path.dirname(os.path.realpath(__file__))
    
    # Create the HTML file path
    html_path = os.path.join(dir_path, "timer.html")
    
    # Create the timer HTML content
    timer_html = f"""
        <div class="timer-container">
            <div id="quiz-timer" class="timer">⏱️ Loading timer...</div>
            <script>
                const endTime = new Date("{end_time_iso}");
                
                function updateTimer() {{
                    const now = new Date();
                    const remaining = Math.max(0, Math.floor((endTime - now) / 1000));
                    const minutes = Math.floor(remaining / 60);
                    const seconds = remaining % 60;
                    const timer = document.getElementById("quiz-timer");
                    
                    if (timer) {{
                        if (remaining > 0) {{
                            timer.innerHTML = `⏱️ Time Remaining: ${{minutes.toString().padStart(2, "0")}}:${{seconds.toString().padStart(2, "0")}}`;
                            requestAnimationFrame(updateTimer);
                        }} else {{
                            timer.innerHTML = "⏱️ Time's Up!";
                            window.parent.location.reload();
                        }}
                    }}
                }}
                
                updateTimer();
            </script>
            <style>
                .timer-container {{
                    padding: 10px;
                    background: #f0f2f6;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    font-family: "Source Sans Pro", sans-serif;
                }}
                .timer {{
                    font-size: 1rem;
                    font-weight: 600;
                    text-align: center;
                    color: rgb(49, 51, 63);
                }}
            </style>
        </div>
    """
    
    # Write the HTML to a file
    with open(html_path, "w") as f:
        f.write(timer_html)
    
    # Create the component
    return components.html(
        open(html_path).read(),
        height=100,
    ) 