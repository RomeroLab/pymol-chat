#import <AVFoundation/AVFoundation.h>
#import <Foundation/Foundation.h>
#import <math.h>

@interface VoiceDetector : NSObject
@property NSTimeInterval startedAt;
@property NSTimeInterval lastVoiceAt;
@property float noiseFloor;
@property NSInteger consecutiveVoice;
@property BOOL heardSpeech;
- (void)resetAt:(NSTimeInterval)now;
- (void)observe:(float)level at:(NSTimeInterval)now;
- (NSString *)stopReasonAt:(NSTimeInterval)now;
@end

@implementation VoiceDetector
- (void)resetAt:(NSTimeInterval)now {
    self.startedAt = now;
    self.lastVoiceAt = 0;
    self.noiseFloor = 0.003f;
    self.consecutiveVoice = 0;
    self.heardSpeech = NO;
}

- (void)observe:(float)level at:(NSTimeInterval)now {
    NSTimeInterval elapsed = now - self.startedAt;
    float threshold = fmaxf(0.014f, self.noiseFloor * 3.2f);
    if (elapsed < 0.35 && !self.heardSpeech) {
        self.noiseFloor = fminf(0.01f, fmaxf(self.noiseFloor, level));
        return;
    }
    if (level >= threshold) {
        self.consecutiveVoice += 1;
        if (self.consecutiveVoice >= 2) {
            self.heardSpeech = YES;
            self.lastVoiceAt = now;
        }
    } else {
        self.consecutiveVoice = 0;
        if (!self.heardSpeech) {
            self.noiseFloor = self.noiseFloor * 0.92f + level * 0.08f;
        }
    }
}

- (NSString *)stopReasonAt:(NSTimeInterval)now {
    NSTimeInterval elapsed = now - self.startedAt;
    if (self.heardSpeech && now - self.lastVoiceAt >= 1.15) return @"silence";
    if (elapsed >= 30.0) return @"maximum";
    if (!self.heardSpeech && elapsed >= 8.0) return @"no_speech";
    return nil;
}
@end

@interface Recorder : NSObject
@property AVAudioEngine *engine;
@property AVAudioFile *outputFile;
@property VoiceDetector *detector;
@property NSURL *outputURL;
@property NSTimer *timer;
@property BOOL stopping;
@property BOOL tapInstalled;
- (instancetype)initWithURL:(NSURL *)url;
- (void)requestPermissionAndStart;
- (void)stop:(NSString *)reason;
@end

@implementation Recorder
- (instancetype)initWithURL:(NSURL *)url {
    self = [super init];
    if (self) {
        self.outputURL = url;
        self.engine = [[AVAudioEngine alloc] init];
        self.detector = [[VoiceDetector alloc] init];
    }
    return self;
}

- (void)requestPermissionAndStart {
    AVAuthorizationStatus status = [AVCaptureDevice authorizationStatusForMediaType:AVMediaTypeAudio];
    if (status == AVAuthorizationStatusAuthorized) {
        [self start];
    } else if (status == AVAuthorizationStatusNotDetermined) {
        [AVCaptureDevice requestAccessForMediaType:AVMediaTypeAudio completionHandler:^(BOOL granted) {
            dispatch_async(dispatch_get_main_queue(), ^{
                if (granted) [self start];
                else [self fail:@"Microphone permission was denied. Enable PyMOL Chat Voice in System Settings → Privacy & Security → Microphone."];
            });
        }];
    } else {
        [self fail:@"Microphone access is disabled. Enable PyMOL Chat Voice in System Settings → Privacy & Security → Microphone."];
    }
}

- (float)rms:(AVAudioPCMBuffer *)buffer {
    float * const *channels = buffer.floatChannelData;
    AVAudioFrameCount frames = buffer.frameLength;
    AVAudioChannelCount channelCount = buffer.format.channelCount;
    if (!channels || frames == 0 || channelCount == 0) return 0;
    double sum = 0;
    for (AVAudioChannelCount channel = 0; channel < channelCount; channel++) {
        for (AVAudioFrameCount frame = 0; frame < frames; frame++) {
            float sample = channels[channel][frame];
            sum += sample * sample;
        }
    }
    return sqrt(sum / (double)(frames * channelCount));
}

- (void)start {
    AVAudioInputNode *input = self.engine.inputNode;
    AVAudioFormat *format = [input outputFormatForBus:0];
    if (format.sampleRate <= 0 || format.channelCount == 0) {
        [self fail:@"No microphone input format is available."];
        return;
    }
    [[NSFileManager defaultManager] removeItemAtURL:self.outputURL error:nil];
    NSError *error = nil;
    self.outputFile = [[AVAudioFile alloc] initForWriting:self.outputURL
                                                settings:format.settings
                                            commonFormat:AVAudioPCMFormatFloat32
                                             interleaved:NO
                                                   error:&error];
    if (!self.outputFile) {
        [self fail:[NSString stringWithFormat:@"Could not create recording: %@", error.localizedDescription]];
        return;
    }
    [self.detector resetAt:NSProcessInfo.processInfo.systemUptime];
    __weak Recorder *weakSelf = self;
    [input installTapOnBus:0 bufferSize:1024 format:format block:^(AVAudioPCMBuffer *buffer, AVAudioTime *when) {
        Recorder *strongSelf = weakSelf;
        if (!strongSelf || strongSelf.stopping) return;
        NSError *writeError = nil;
        if (![strongSelf.outputFile writeFromBuffer:buffer error:&writeError]) {
            dispatch_async(dispatch_get_main_queue(), ^{
                [strongSelf fail:[NSString stringWithFormat:@"Could not write microphone audio: %@", writeError.localizedDescription]];
            });
            return;
        }
        float level = [strongSelf rms:buffer];
        dispatch_async(dispatch_get_main_queue(), ^{
            [strongSelf.detector observe:level at:NSProcessInfo.processInfo.systemUptime];
        });
    }];
    self.tapInstalled = YES;
    [self.engine prepare];
    if (![self.engine startAndReturnError:&error]) {
        [input removeTapOnBus:0];
        self.tapInstalled = NO;
        [self fail:[NSString stringWithFormat:@"Could not start microphone recording: %@", error.localizedDescription]];
        return;
    }
    self.timer = [NSTimer scheduledTimerWithTimeInterval:0.1 repeats:YES block:^(NSTimer *timer) {
        Recorder *strongSelf = weakSelf;
        NSString *reason = [strongSelf.detector stopReasonAt:NSProcessInfo.processInfo.systemUptime];
        if (reason) [strongSelf stop:reason];
    }];
    puts("recording");
    fflush(stdout);
}

- (void)stop:(NSString *)reason {
    if (self.stopping) return;
    self.stopping = YES;
    [self.timer invalidate];
    if (self.tapInstalled) {
        [self.engine.inputNode removeTapOnBus:0];
        self.tapInstalled = NO;
    }
    [self.engine stop];
    self.outputFile = nil;
    if ([reason isEqualToString:@"no_speech"]) {
        [self fail:@"No speech detected. Click the microphone and try again."];
        return;
    }
    puts("done");
    fflush(stdout);
    exit(EXIT_SUCCESS);
}

- (void)fail:(NSString *)message {
    if (self.stopping == NO) self.stopping = YES;
    [self.timer invalidate];
    if (self.tapInstalled) {
        [self.engine.inputNode removeTapOnBus:0];
        self.tapInstalled = NO;
    }
    if (self.engine.isRunning) {
        [self.engine stop];
    }
    self.outputFile = nil;
    fprintf(stderr, "%s\n", message.UTF8String);
    fflush(stderr);
    exit(EXIT_FAILURE);
}
@end

static void RunSelfTest(void) {
    VoiceDetector *detector = [[VoiceDetector alloc] init];
    [detector resetAt:0];
    [detector observe:0.1f at:0.5];
    [detector observe:0.1f at:0.6];
    NSCAssert(detector.heardSpeech, @"Speech was not detected");
    NSCAssert([detector stopReasonAt:1.5] == nil, @"Stopped too soon");
    NSCAssert([[detector stopReasonAt:1.8] isEqualToString:@"silence"], @"Silence was not detected");
    puts("voice detector self-test passed");
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc == 2 && strcmp(argv[1], "--self-test") == 0) {
            RunSelfTest();
            return EXIT_SUCCESS;
        }
        if (argc != 2) {
            fprintf(stderr, "Usage: PyMOLChatVoice output.wav\n");
            return EXIT_FAILURE;
        }
        Recorder *recorder = [[Recorder alloc] initWithURL:[NSURL fileURLWithPath:@(argv[1])]];
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
            NSData *data = [[NSFileHandle fileHandleWithStandardInput] availableData];
            if (data.length > 0) dispatch_async(dispatch_get_main_queue(), ^{ [recorder stop:@"manual"]; });
        });
        [recorder requestPermissionAndStart];
        [[NSRunLoop mainRunLoop] run];
    }
    return EXIT_SUCCESS;
}
