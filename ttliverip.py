import json, sys, requests, os, argparse, subprocess
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def grabfulldata(videourl):
    headers = {"User-Agent":"Mozilla/5.0 (iPhone; CPU OS 10_15_5 (Ergänzendes Update) like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.1 Mobile/14E304 Safari/605.1.15"}
    response = requests.get(videourl, headers=headers, allow_redirects=True)
    html_doc = response.content
    soup = BeautifulSoup(html_doc, 'html.parser')
    return json.loads(soup.find('script', id='SIGI_STATE').text)

def getlive(url):
    sigistate = grabfulldata(url)
    rawstreamdata = json.loads(sigistate['LiveRoomMobile']['userInfo']['liveRoom']['streamData']['pull_data']['stream_data'])
    streamdata = {}
    streamdata['streams'] = {}
    for k in rawstreamdata['data']:
        streamdata['streams'][k] = rawstreamdata['data'][k]['main']['flv']
    streamdata['user'] = sigistate['LiveRoomMobile']['userInfo']['user']
    streamdata['title'] = sigistate['LiveRoomMobile']['userInfo']['liveRoom']['title']
    streamdata['startTime'] = sigistate['LiveRoomMobile']['userInfo']['liveRoom']['startTime']
    return streamdata

def probestreams(instreams):
    rawstreamprobe = {}
    for k in instreams:
        process = subprocess.Popen('ffprobe -v quiet -print_format json -print_format json -show_format -show_streams ' + instreams[k], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        errcode = process.returncode
        rawstreamprobe[k] = json.loads(out)
    streamprobe = []
    for k in rawstreamprobe:
        videostream = {}
        for i in rawstreamprobe[k]['streams']:
            if i['codec_type'] == "video":
                for detail in ['codec_name','width','height','avg_frame_rate']:
                    videostream[detail] = i[detail]
                videostream['quality_sh'] = str(min(i['height'], i['width'])) + 'p'
                videostream['quality_sh'] += i['avg_frame_rate'].rstrip('/1')
                videostream['stream_name'] = k
        streamprobe.append(videostream)
    return streamprobe

if __name__=='__main__':
    parser = argparse.ArgumentParser(
                    prog='ttliverip',
                    description='records tiktok livestreams.')
    parser.add_argument('-O', '--output', help="output path / filename", metavar="[path]", required=False)
    parser.add_argument('-q', '--quality', help="quality selection. use -Q for a list of options", metavar="[stream]", required=False)
    parser.add_argument('-Q', '--quality-options', action='store_true', help="get quality options for -q", required=False)
    parser.add_argument('-v', '--verbose', action='store_true', help="show ffmpeg output.", required=False)
    parser.add_argument('--vlc', help="open live in vlc while recording. requires vlc in env variables", action='store_true', required=False)
    parser.add_argument('url', help="url of the live.")

    args = parser.parse_args()
    url = args.url
    print("loading live details...")
    try: livedetails = getlive(url)
    except:
        print("failed to load live details, live does not exist")
        sys.exit()
    print("loaded successfully!")
    if args.quality_options==False:
        useq = "origin"

        if args.quality==None:
            print('quality not specified. using "origin" as quality for recording.')
        else:
            if args.quality not in livedetails['streams'].keys():
                print("quality specified is not an option. Use -Q for a list of options")
                sys.exit()
            else:
                print('selecting "' + args.quality + '" as quality for recording.')
            useq = args.quality()
        
        flvurl = livedetails['streams'][useq]
        filename = os.path.basename(urlparse(flvurl).path).replace('.flv', '.mkv')
        if args.output!=None:
            if os.path.exists(args.output):
                pass
            elif os.access(os.path.dirname(args.output), os.W_OK):
                pass
            else:
                print("the output file path given is not a valid file path.")
                sys.exit()
            if not (args.output.endswith('.mp4') or args.output.endswith('.mkv')):
                print("the output file must end in .mp4 or .mkv.")
                sys.exit()
            filename = args.output
        else:
            print("output path not specified. using generated filename from tiktok servers...")
        if os.path.isfile(filename):
            try:
                yorn = input('the file "' + os.path.basename(filename) + '" already exists. would you like to overwrite it? (y/n) ')
            except KeyboardInterrupt:
                sys.exit()
            if yorn != "y":
                print('program exited - File "' + os.path.basename(filename) + '" already exists.')
                sys.exit()
        command = "ffmpeg -y"
        if not args.verbose:
            command += " -v quiet -stats"
        command += " -i " + flvurl + ' "' + filename + '"'
        print('saving recording to "' + filename + '"')
        print('starting recording... (press ctrl + c to stop)')
        usevlc = args.vlc
        vlcpopen = None
        if usevlc:
            try:
                vlcpopen = subprocess.Popen(['vlc', flvurl])
            except:
                print("vlc is not on path. cannot run")
                usevlc = False
        try:
            ffmpegprocess = subprocess.Popen(command)
            ffmpegprocess.wait()
            if usevlc:
                vlcpopen.kill()
        except KeyboardInterrupt:
            print('user stopped recording. saved to "' + filename + '"')
            if usevlc:
                vlcpopen.kill()
        except OSError:
            print('\nffmpeg/ffprobe is either not installed, or not on the PATH.\nplease install them, then read this to add to PATH: https://superuser.com/a/1716401')
            
    else:
        print("probing streams...")
        try: probe = probestreams(livedetails['streams'])
        except:
            print("\nsomething went wrong.")
            print("you may not have ffmpeg/ffprobe installed, or not on the PATH.\nplease install them, then read this to add to PATH: https://superuser.com/a/1716401")
            sys.exit()
        print('\nquality options:')
        for i in probe:
            print(i['stream_name'] + ' | (' + i['quality_sh'] + ')')