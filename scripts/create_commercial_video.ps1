param(
    [string]$Source = "",
    [string]$OutputWide = "",
    [string]$OutputVertical = ""
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw "ffmpeg nao foi encontrado no PATH."
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if ([string]::IsNullOrWhiteSpace($Source)) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $sourceFolder = "Cap Cut V$([char]0x00ED)deos Salvos"
    $Source = Join-Path (Join-Path $desktop $sourceFolder) "0501 (1).mp4"
}

if ([string]::IsNullOrWhiteSpace($OutputWide)) {
    $OutputWide = Join-Path $repoRoot "dist\TorvixTracker_Comercial_16x9.mp4"
}

if ([string]::IsNullOrWhiteSpace($OutputVertical)) {
    $OutputVertical = Join-Path $repoRoot "dist\TorvixTracker_Comercial_9x16.mp4"
}

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Video de origem nao encontrado: $Source"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputWide) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputVertical) | Out-Null

foreach ($output in @($OutputWide, $OutputVertical)) {
    if (Test-Path -LiteralPath $output) {
        Remove-Item -LiteralPath $output -Force
    }
}

$font = "C\:/Windows/Fonts/bahnschrift.ttf"
$duration = 43.0
$transition = 0.30
$workDir = Join-Path $env:TEMP ("torvix_commercial_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $workDir | Out-Null

function New-TorvixCommercialMusic {
    param(
        [string]$Path,
        [double]$Duration = 43.0,
        [int]$SampleRate = 44100
    )

    if (-not ("TorvixCommercialMusicWriter" -as [type])) {
        Add-Type -TypeDefinition @"
using System;
using System.IO;

public static class TorvixCommercialMusicWriter
{
    public static void WriteWav(string path, double duration, int sampleRate)
    {
        int samples = (int)(duration * sampleRate);
        int channels = 2;
        int bytesPerSample = 2;
        int byteRate = sampleRate * channels * bytesPerSample;
        int dataSize = samples * channels * bytesPerSample;

        using (FileStream fs = new FileStream(path, FileMode.Create, FileAccess.Write))
        using (BinaryWriter bw = new BinaryWriter(fs))
        {
            bw.Write(new byte[] { (byte)'R', (byte)'I', (byte)'F', (byte)'F' });
            bw.Write(36 + dataSize);
            bw.Write(new byte[] { (byte)'W', (byte)'A', (byte)'V', (byte)'E' });
            bw.Write(new byte[] { (byte)'f', (byte)'m', (byte)'t', (byte)' ' });
            bw.Write(16);
            bw.Write((short)1);
            bw.Write((short)channels);
            bw.Write(sampleRate);
            bw.Write(byteRate);
            bw.Write((short)(channels * bytesPerSample));
            bw.Write((short)16);
            bw.Write(new byte[] { (byte)'d', (byte)'a', (byte)'t', (byte)'a' });
            bw.Write(dataSize);

            double[][] chords = new double[][]
            {
                new double[] { 110.00, 130.81, 164.81, 220.00 },
                new double[] { 98.00, 123.47, 146.83, 196.00 },
                new double[] { 82.41, 123.47, 164.81, 246.94 },
                new double[] { 87.31, 130.81, 174.61, 220.00 }
            };

            for (int i = 0; i < samples; i++)
            {
                double t = i / (double)sampleRate;
                double ramp = Math.Min(1.0, Math.Max(0.0, t / 14.0));
                double outro = Math.Min(1.0, Math.Max(0.0, (duration - t) / 2.2));
                double barPos = t - Math.Floor(t / 4.0) * 4.0;
                int bar = ((int)(t / 4.0)) % chords.Length;
                double[] chord = chords[bar];

                double padEnv = Math.Min(1.0, Math.Min(barPos / 0.45, (4.0 - barPos) / 0.7));
                double pad = 0.0;
                for (int n = 0; n < chord.Length; n++)
                {
                    pad += Math.Sin(2.0 * Math.PI * chord[n] * t) / chord.Length;
                    pad += 0.20 * Math.Sin(2.0 * Math.PI * chord[n] * 2.0 * t) / chord.Length;
                }

                double beat = t * 2.0;
                int step = ((int)beat) % 8;
                double stepPos = beat - Math.Floor(beat);
                double arpFreq = chord[step % chord.Length] * (step < 4 ? 2.0 : 4.0);
                double arp = Math.Sin(2.0 * Math.PI * arpFreq * t) * Math.Exp(-stepPos * 8.5);

                double kickPos = t - Math.Floor(t);
                double kick = Math.Sin(2.0 * Math.PI * (58.0 - 22.0 * kickPos) * t) * Math.Exp(-kickPos * 18.0);

                double hatStep = t * 4.0;
                double hatPos = hatStep - Math.Floor(hatStep);
                double hat = (Math.Sin(2.0 * Math.PI * 6200.0 * t) + 0.45 * Math.Sin(2.0 * Math.PI * 7900.0 * t)) * Math.Exp(-hatPos * 28.0);

                double snarePos = (t + 0.5) - Math.Floor(t + 0.5);
                double snareGate = (((int)(t * 2.0)) % 4 == 2) ? 1.0 : 0.0;
                double snare = Math.Sin(2.0 * Math.PI * 180.0 * t) * Math.Exp(-snarePos * 18.0) * snareGate;

                double pulse = Math.Sin(2.0 * Math.PI * 55.0 * t) * (0.6 + 0.4 * Math.Sin(2.0 * Math.PI * 0.25 * t));
                double value = outro * ((0.28 * pad * padEnv) + (0.10 * arp * ramp) + (0.20 * kick) + (0.035 * hat * ramp) + (0.09 * snare * ramp) + (0.04 * pulse));

                if (value > 0.92) value = 0.92;
                if (value < -0.92) value = -0.92;

                short sample = (short)(value * short.MaxValue);
                bw.Write(sample);
                bw.Write(sample);
            }
        }
    }
}
"@
    }

    [TorvixCommercialMusicWriter]::WriteWav($Path, $Duration, $SampleRate)
}

function Invoke-Ffmpeg {
    param([scriptblock]$Command, [string]$ErrorMessage)
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $ErrorMessage
    }
}

$segments = @(
    @{ Start = "00:02:37"; Duration = 3.2; Zoom = 1.08; Focus = "center" },
    @{ Start = "00:00:18"; Duration = 3.0; Zoom = 1.06; Focus = "center" },
    @{ Start = "00:00:30"; Duration = 3.2; Zoom = 1.05; Focus = "center" },
    @{ Start = "00:01:10"; Duration = 3.4; Zoom = 1.08; Focus = "center" },
    @{ Start = "00:01:20"; Duration = 3.5; Zoom = 1.10; Focus = "left" },
    @{ Start = "00:01:29"; Duration = 3.0; Zoom = 1.08; Focus = "center" },
    @{ Start = "00:01:50"; Duration = 3.5; Zoom = 1.10; Focus = "right" },
    @{ Start = "00:02:00"; Duration = 3.6; Zoom = 1.11; Focus = "right" },
    @{ Start = "00:02:20"; Duration = 3.2; Zoom = 1.06; Focus = "center" },
    @{ Start = "00:02:39"; Duration = 3.4; Zoom = 1.08; Focus = "left" },
    @{ Start = "00:03:20"; Duration = 3.6; Zoom = 1.10; Focus = "right" },
    @{ Start = "00:04:30"; Duration = 3.6; Zoom = 1.09; Focus = "center" },
    @{ Start = "00:05:20"; Duration = 3.6; Zoom = 1.06; Focus = "center" },
    @{ Start = "00:05:30"; Duration = 4.2; Zoom = 1.08; Focus = "center" }
)

try {
    $clips = @()

    for ($i = 0; $i -lt $segments.Count; $i++) {
        $clip = Join-Path $workDir ("clip_{0:D2}.mp4" -f $i)
        $clips += $clip
        $scaleW = [Math]::Ceiling((1920 * [double]$segments[$i].Zoom) / 2) * 2
        $scaleH = [Math]::Ceiling((1080 * [double]$segments[$i].Zoom) / 2) * 2
        $cropX = "(iw-ow)/2"
        if ($segments[$i].Focus -eq "left") { $cropX = "(iw-ow)*0.25" }
        if ($segments[$i].Focus -eq "right") { $cropX = "(iw-ow)*0.75" }
        $videoFilter = "scale=${scaleW}:${scaleH},crop=1920:1080:x=${cropX}:y=(ih-oh)/2,fps=30,format=yuv420p,setsar=1"

        Invoke-Ffmpeg -ErrorMessage "Falha ao extrair o trecho comercial $i." -Command {
            ffmpeg `
                -hide_banner `
                -y `
                -ss $segments[$i].Start `
                -t $segments[$i].Duration `
                -i $Source `
                -vf $videoFilter `
                -af "aresample=44100" `
                -c:v libx264 `
                -preset veryfast `
                -crf 20 `
                -c:a aac `
                -b:a 160k `
                -movflags +faststart `
                $clip
        }
    }

    $base = Join-Path $workDir "commercial_base.mp4"
    $initVideo = @()
    $xfades = @()
    $initAudio = @()
    $afades = @()
    $running = 0.0

    for ($i = 0; $i -lt $segments.Count; $i++) {
        $initVideo += "[$i`:v]settb=AVTB,setpts=PTS-STARTPTS[v$i]"
        $initAudio += "[$i`:a]asetpts=PTS-STARTPTS[a$i]"
    }

    for ($i = 1; $i -lt $segments.Count; $i++) {
        $running += [double]$segments[$i - 1].Duration
        $offset = [Math]::Round($running - ($transition * $i), 2).ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
        $left = if ($i -eq 1) { "v0" } else { "vx$($i - 1)" }
        $right = "v$i"
        $out = if ($i -eq ($segments.Count - 1)) { "vout" } else { "vx$i" }
        $transitionName = if (($i % 4) -eq 0) { "smoothleft" } else { "fade" }
        $xfades += "[$left][$right]xfade=transition=${transitionName}:duration=$transition`:offset=$offset[$out]"

        $audioLeft = if ($i -eq 1) { "a0" } else { "ax$($i - 1)" }
        $audioRight = "a$i"
        $audioOut = if ($i -eq ($segments.Count - 1)) { "aout" } else { "ax$i" }
        $afades += "[$audioLeft][$audioRight]acrossfade=d=$transition`:c1=tri:c2=tri[$audioOut]"
    }

    $transitionFilter = (($initVideo + $xfades + $initAudio + $afades) -join ";") + ";[vout]format=yuv420p[vfinal]"

    $transitionArgs = @("-hide_banner", "-y")
    foreach ($clip in $clips) {
        $transitionArgs += @("-i", $clip)
    }
    $transitionArgs += @(
        "-filter_complex", $transitionFilter,
        "-map", "[vfinal]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        $base
    )

    & ffmpeg @transitionArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao aplicar transicoes do comercial."
    }

    $music = Join-Path $workDir "commercial_music.wav"
    New-TorvixCommercialMusic -Path $music -Duration $duration

    $wideFilter = @'
[0:v]drawbox=x=0:y=0:w=1920:h=1080:color=black@0.08:t=fill,
drawbox=x=64:y=58:w=420:h=3:color=0x00E5FF@0.85:t=fill:enable='between(t,0,43)',
drawbox=x=64:y=73:w=190:h=2:color=white@0.55:t=fill:enable='between(t,0,43)',
drawbox=x=0:y=805:w=1920:h=275:color=black@0.58:t=fill,
drawbox=x=64:y=805:w=560:h=3:color=0x00E5FF@0.9:t=fill,
drawtext=fontfile='__FONT__':text='TORVIX TRACKER':x=64:y=96:fontsize=34:fontcolor=0x00E5FF:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0,
drawtext=fontfile='__FONT__':text='CONTROLE A CAMERA COM A WEBCAM':x=64:y=858:fontsize=64:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,0,3.0)',
drawtext=fontfile='__FONT__':text='Hook imediato - rastreamento no simulador':x=68:y=930:fontsize=32:fontcolor=0xD8FBFF:enable='between(t,0,3.0)',
drawtext=fontfile='__FONT__':text='OLHAR PARA ESPELHOS NAO PRECISA QUEBRAR O RITMO':x=64:y=858:fontsize=54:fontcolor=white:shadowcolor=0x00E5FF@0.55:shadowx=0:shadowy=0:enable='between(t,3.0,8.7)',
drawtext=fontfile='__FONT__':text='Mais imersao no ETS2 e ATS':x=68:y=930:fontsize=34:fontcolor=0xD8FBFF:enable='between(t,3.0,8.7)',
drawtext=fontfile='__FONT__':text='RASTREAMENTO EM TEMPO REAL':x=64:y=858:fontsize=64:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,8.7,16.6)',
drawtext=fontfile='__FONT__':text='Cabeca e olhar capturados pela webcam':x=68:y=930:fontsize=34:fontcolor=0xD8FBFF:enable='between(t,8.7,16.6)',
drawtext=fontfile='__FONT__':text='AJUSTE FINO PARA O SEU ESTILO':x=64:y=858:fontsize=64:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,16.6,25.1)',
drawtext=fontfile='__FONT__':text='Deadzone + suavizacao + resposta + curvas':x=68:y=930:fontsize=34:fontcolor=0xD8FBFF:enable='between(t,16.6,25.1)',
drawtext=fontfile='__FONT__':text='FLUIDEZ PARA DIRIGIR':x=64:y=858:fontsize=64:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,25.1,33.7)',
drawtext=fontfile='__FONT__':text='Espelhos + curvas + cabine com movimento natural':x=68:y=930:fontsize=34:fontcolor=0xD8FBFF:enable='between(t,25.1,33.7)',
drawtext=fontfile='__FONT__':text='SAIDA PARA SIMULADORES':x=64:y=858:fontsize=64:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,33.7,38.9)',
drawtext=fontfile='__FONT__':text='FreeTrack e TrackIR compativel':x=68:y=930:fontsize=34:fontcolor=0xD8FBFF:enable='between(t,33.7,38.9)',
drawtext=fontfile='__FONT__':text='TORVIX TRACKER PRO':x=64:y=858:fontsize=70:fontcolor=white:shadowcolor=0x00E5FF@0.7:shadowx=0:shadowy=0:enable='between(t,38.9,43)',
drawtext=fontfile='__FONT__':text='Compre e baixe no site - R$ 19\,99':x=68:y=935:fontsize=38:fontcolor=0x00E5FF:shadowcolor=0x00E5FF@0.55:shadowx=0:shadowy=0:enable='between(t,38.9,43)',
fade=t=in:st=0:d=0.25,fade=t=out:st=42.25:d=0.75,format=yuv420p,setsar=1[vout];
[0:a]volume=0.18,afade=t=in:st=0:d=0.25,afade=t=out:st=42.25:d=0.75[orig];
[1:a]volume=0.78,afade=t=in:st=0:d=0.6,afade=t=out:st=41:d=2[music];
[orig][music]amix=inputs=2:duration=shortest:normalize=0,alimiter=limit=0.95[aout]
'@.Replace("__FONT__", $font)

    Invoke-Ffmpeg -ErrorMessage "Falha ao gerar comercial 16:9." -Command {
        ffmpeg `
            -hide_banner `
            -y `
            -i $base `
            -i $music `
            -t $duration `
            -filter_complex $wideFilter `
            -map "[vout]" `
            -map "[aout]" `
            -c:v libx264 `
            -preset medium `
            -crf 19 `
            -r 30 `
            -c:a aac `
            -b:a 160k `
            -movflags +faststart `
            $OutputWide
    }

    $verticalFilter = @'
[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=24,eq=brightness=-0.22:saturation=1.25[bg];
[0:v]scale=1080:-1[fg];
[bg][fg]overlay=x=0:y=520,drawbox=x=0:y=0:w=1080:h=410:color=black@0.54:t=fill,
drawbox=x=0:y=1238:w=1080:h=682:color=black@0.58:t=fill,
drawbox=x=70:y=92:w=330:h=4:color=0x00E5FF@0.9:t=fill,
drawbox=x=70:y=1240:w=420:h=4:color=0x00E5FF@0.9:t=fill,
drawtext=fontfile='__FONT__':text='TORVIX TRACKER':x=70:y=130:fontsize=42:fontcolor=0x00E5FF:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0,
drawtext=fontfile='__FONT__':text='CONTROLE A CAMERA':x=70:y=1265:fontsize=64:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,0,3.0)',
drawtext=fontfile='__FONT__':text='COM A WEBCAM':x=70:y=1340:fontsize=64:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,0,3.0)',
drawtext=fontfile='__FONT__':text='Rastreamento no simulador':x=74:y=1424:fontsize=36:fontcolor=0xD8FBFF:enable='between(t,0,3.0)',
drawtext=fontfile='__FONT__':text='MAIS IMERSAO':x=70:y=1265:fontsize=68:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,3.0,8.7)',
drawtext=fontfile='__FONT__':text='NO ETS2 E ATS':x=70:y=1344:fontsize=60:fontcolor=white:shadowcolor=0x00E5FF@0.55:shadowx=0:shadowy=0:enable='between(t,3.0,8.7)',
drawtext=fontfile='__FONT__':text='Sem quebrar o ritmo':x=74:y=1426:fontsize=36:fontcolor=0xD8FBFF:enable='between(t,3.0,8.7)',
drawtext=fontfile='__FONT__':text='TEMPO REAL':x=70:y=1265:fontsize=76:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,8.7,16.6)',
drawtext=fontfile='__FONT__':text='Cabeca + olhar pela webcam':x=74:y=1360:fontsize=38:fontcolor=0xD8FBFF:enable='between(t,8.7,16.6)',
drawtext=fontfile='__FONT__':text='AJUSTE FINO':x=70:y=1265:fontsize=76:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,16.6,25.1)',
drawtext=fontfile='__FONT__':text='Deadzone + resposta + curvas':x=74:y=1360:fontsize=38:fontcolor=0xD8FBFF:enable='between(t,16.6,25.1)',
drawtext=fontfile='__FONT__':text='FLUIDEZ':x=70:y=1265:fontsize=80:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,25.1,33.7)',
drawtext=fontfile='__FONT__':text='Espelhos + curvas + cabine':x=74:y=1360:fontsize=38:fontcolor=0xD8FBFF:enable='between(t,25.1,33.7)',
drawtext=fontfile='__FONT__':text='SIMULADORES':x=70:y=1265:fontsize=74:fontcolor=white:shadowcolor=0x00E5FF@0.65:shadowx=0:shadowy=0:enable='between(t,33.7,38.9)',
drawtext=fontfile='__FONT__':text='FreeTrack e TrackIR compativel':x=74:y=1360:fontsize=38:fontcolor=0xD8FBFF:enable='between(t,33.7,38.9)',
drawtext=fontfile='__FONT__':text='TORVIX TRACKER PRO':x=70:y=1265:fontsize=64:fontcolor=white:shadowcolor=0x00E5FF@0.7:shadowx=0:shadowy=0:enable='between(t,38.9,43)',
drawtext=fontfile='__FONT__':text='R$ 19\,99':x=70:y=1345:fontsize=72:fontcolor=0x00E5FF:shadowcolor=0x00E5FF@0.7:shadowx=0:shadowy=0:enable='between(t,38.9,43)',
drawtext=fontfile='__FONT__':text='Compre e baixe no site':x=74:y=1432:fontsize=38:fontcolor=0xD8FBFF:enable='between(t,38.9,43)',
fade=t=in:st=0:d=0.25,fade=t=out:st=42.25:d=0.75,format=yuv420p,setsar=1[vout];
[0:a]volume=0.18,afade=t=in:st=0:d=0.25,afade=t=out:st=42.25:d=0.75[orig];
[1:a]volume=0.78,afade=t=in:st=0:d=0.6,afade=t=out:st=41:d=2[music];
[orig][music]amix=inputs=2:duration=shortest:normalize=0,alimiter=limit=0.95[aout]
'@.Replace("__FONT__", $font)

    Invoke-Ffmpeg -ErrorMessage "Falha ao gerar comercial 9:16." -Command {
        ffmpeg `
            -hide_banner `
            -y `
            -i $base `
            -i $music `
            -t $duration `
            -filter_complex $verticalFilter `
            -map "[vout]" `
            -map "[aout]" `
            -c:v libx264 `
            -preset medium `
            -crf 20 `
            -r 30 `
            -c:a aac `
            -b:a 160k `
            -movflags +faststart `
            $OutputVertical
    }

    Write-Host "Comercial 16:9 gerado em: $OutputWide"
    Write-Host "Comercial 9:16 gerado em: $OutputVertical"
}
finally {
    if ((Test-Path -LiteralPath $workDir) -and ($env:TORVIX_KEEP_TEMP -ne "1")) {
        Remove-Item -LiteralPath $workDir -Recurse -Force
    }
}
