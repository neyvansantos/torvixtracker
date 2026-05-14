param(
    [string]$Source = "",
    [string]$Output = ""
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

if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $repoRoot "dist\TorvixTracker_Apresentacao_16x9.mp4"
}

$logo = Join-Path $repoRoot "website\public\torvix-logo.png"
$font = "C\:/Windows/Fonts/arial.ttf"

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Video de origem nao encontrado: $Source"
}

if (-not (Test-Path -LiteralPath $logo)) {
    throw "Logo nao encontrado: $logo"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output) | Out-Null

if (Test-Path -LiteralPath $Output) {
    Remove-Item -LiteralPath $Output -Force
}

$workDir = Join-Path $env:TEMP ("torvix_presentation_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $workDir | Out-Null

function New-TorvixBackgroundMusic {
    param(
        [string]$Path,
        [double]$Duration = 59.0,
        [int]$SampleRate = 44100
    )

    if (-not ("TorvixMusicWriter" -as [type])) {
        Add-Type -TypeDefinition @"
using System;
using System.IO;

public static class TorvixMusicWriter
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
                new double[] { 87.31, 130.81, 174.61, 220.00 },
                new double[] { 98.00, 123.47, 146.83, 196.00 },
                new double[] { 82.41, 123.47, 164.81, 246.94 }
            };

            for (int i = 0; i < samples; i++)
            {
                double t = i / (double)sampleRate;
                int bar = ((int)(t / 4.0)) % chords.Length;
                double barPos = t - Math.Floor(t / 4.0) * 4.0;
                double[] chord = chords[bar];

                double chordEnv = Math.Min(1.0, Math.Min(barPos / 0.55, (4.0 - barPos) / 0.75));
                double pad = 0.0;
                for (int n = 0; n < chord.Length; n++)
                {
                    pad += Math.Sin(2.0 * Math.PI * chord[n] * t) / chord.Length;
                    pad += 0.32 * Math.Sin(2.0 * Math.PI * chord[n] * 2.0 * t) / chord.Length;
                }

                int step = ((int)(t * 2.0)) % 8;
                double stepPos = (t * 2.0) - Math.Floor(t * 2.0);
                double arpFreq = chord[step % chord.Length] * (step < 4 ? 2.0 : 4.0);
                double arpEnv = Math.Exp(-stepPos * 7.5);
                double arp = Math.Sin(2.0 * Math.PI * arpFreq * t) * arpEnv;

                double beatPos = t - Math.Floor(t);
                double kickEnv = Math.Exp(-beatPos * 16.0);
                double kick = Math.Sin(2.0 * Math.PI * (55.0 - 18.0 * beatPos) * t) * kickEnv;
                double shimmer = Math.Sin(2.0 * Math.PI * 880.0 * t) * Math.Exp(-stepPos * 12.0);
                double slowFade = Math.Min(1.0, Math.Min(t / 2.0, (duration - t) / 2.0));
                double value = slowFade * ((0.34 * pad * chordEnv) + (0.11 * arp) + (0.16 * kick) + (0.025 * shimmer));

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

    [TorvixMusicWriter]::WriteWav($Path, $Duration, $SampleRate)
}

$segments = @(
    @{ Start = "00:00:18"; Duration = 8 },
    @{ Start = "00:01:10"; Duration = 8 },
    @{ Start = "00:01:50"; Duration = 9 },
    @{ Start = "00:02:21"; Duration = 9 },
    @{ Start = "00:03:10"; Duration = 9 },
    @{ Start = "00:04:30"; Duration = 9 },
    @{ Start = "00:05:20"; Duration = 10 }
)

try {
    $clips = @()

    for ($i = 0; $i -lt $segments.Count; $i++) {
        $clip = Join-Path $workDir ("clip_{0:D2}.mp4" -f $i)
        $clips += $clip

        & ffmpeg `
            -hide_banner `
            -y `
            -ss $segments[$i].Start `
            -t $segments[$i].Duration `
            -i $Source `
            -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=yuv420p" `
            -af "aresample=44100" `
            -c:v libx264 `
            -preset veryfast `
            -crf 21 `
            -c:a aac `
            -b:a 160k `
            -movflags +faststart `
            $clip

        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao extrair o trecho $i."
        }
    }

    $transitioned = Join-Path $workDir "transitioned.mp4"
    $transitionFilter = @"
[0:v]settb=AVTB,setpts=PTS-STARTPTS[v0];[1:v]settb=AVTB,setpts=PTS-STARTPTS[v1];[2:v]settb=AVTB,setpts=PTS-STARTPTS[v2];[3:v]settb=AVTB,setpts=PTS-STARTPTS[v3];[4:v]settb=AVTB,setpts=PTS-STARTPTS[v4];[5:v]settb=AVTB,setpts=PTS-STARTPTS[v5];[6:v]settb=AVTB,setpts=PTS-STARTPTS[v6];
[v0][v1]xfade=transition=fade:duration=0.5:offset=7.5[v01];
[v01][v2]xfade=transition=fade:duration=0.5:offset=15.0[v02];
[v02][v3]xfade=transition=fade:duration=0.5:offset=23.5[v03];
[v03][v4]xfade=transition=fade:duration=0.5:offset=32.0[v04];
[v04][v5]xfade=transition=fade:duration=0.5:offset=40.5[v05];
[v05][v6]xfade=transition=fade:duration=0.5:offset=49.0,format=yuv420p[vout];
[0:a]asetpts=PTS-STARTPTS[a0];[1:a]asetpts=PTS-STARTPTS[a1];[2:a]asetpts=PTS-STARTPTS[a2];[3:a]asetpts=PTS-STARTPTS[a3];[4:a]asetpts=PTS-STARTPTS[a4];[5:a]asetpts=PTS-STARTPTS[a5];[6:a]asetpts=PTS-STARTPTS[a6];
[a0][a1]acrossfade=d=0.5:c1=tri:c2=tri[a01];
[a01][a2]acrossfade=d=0.5:c1=tri:c2=tri[a02];
[a02][a3]acrossfade=d=0.5:c1=tri:c2=tri[a03];
[a03][a4]acrossfade=d=0.5:c1=tri:c2=tri[a04];
[a04][a5]acrossfade=d=0.5:c1=tri:c2=tri[a05];
[a05][a6]acrossfade=d=0.5:c1=tri:c2=tri[aout]
"@

    & ffmpeg `
        -hide_banner `
        -y `
        -i $clips[0] `
        -i $clips[1] `
        -i $clips[2] `
        -i $clips[3] `
        -i $clips[4] `
        -i $clips[5] `
        -i $clips[6] `
        -filter_complex $transitionFilter `
        -map "[vout]" `
        -map "[aout]" `
        -c:v libx264 `
        -preset veryfast `
        -crf 21 `
        -c:a aac `
        -b:a 160k `
        -movflags +faststart `
        $transitioned

    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao aplicar as transicoes."
    }

    $music = Join-Path $workDir "background_music.wav"
    New-TorvixBackgroundMusic -Path $music -Duration 59.0

    $filter = @"
[1:v]scale=170:-1,format=rgba,colorchannelmixer=aa=0.88[logo];
[0:v]drawbox=x=0:y=870:w=1920:h=210:color=black@0.56:t=fill,
drawtext=fontfile='$font':text='TORVIX TRACKER':x=72:y=895:fontsize=26:fontcolor=0x00E5FF,
drawtext=fontfile='$font':text='Torvix Tracker':x=72:y=936:fontsize=58:fontcolor=white:enable='between(t,0,7.7)',
drawtext=fontfile='$font':text='Rastreamento por webcam para ETS2 e ATS':x=72:y=1004:fontsize=32:fontcolor=0xD7F9FC:enable='between(t,0,7.7)',
drawtext=fontfile='$font':text='Sua camera vira controle':x=72:y=936:fontsize=58:fontcolor=white:enable='between(t,7.7,15.3)',
drawtext=fontfile='$font':text='Cabeca e olhar capturados em tempo real':x=72:y=1004:fontsize=32:fontcolor=0xD7F9FC:enable='between(t,7.7,15.3)',
drawtext=fontfile='$font':text='Ajuste fino de movimento':x=72:y=936:fontsize=58:fontcolor=white:enable='between(t,15.3,23.9)',
drawtext=fontfile='$font':text='Deadzone, suavizacao, resposta e curvas':x=72:y=1004:fontsize=32:fontcolor=0xD7F9FC:enable='between(t,15.3,23.9)',
drawtext=fontfile='$font':text='Olhe para espelhos e curvas':x=72:y=936:fontsize=58:fontcolor=white:enable='between(t,23.9,32.4)',
drawtext=fontfile='$font':text='Mais imersao sem hardware caro':x=72:y=1004:fontsize=32:fontcolor=0xD7F9FC:enable='between(t,23.9,32.4)',
drawtext=fontfile='$font':text='Perfis e calibracao':x=72:y=936:fontsize=58:fontcolor=white:enable='between(t,32.4,41.0)',
drawtext=fontfile='$font':text='Centralize, ajuste e salve seu jeito de jogar':x=72:y=1004:fontsize=32:fontcolor=0xD7F9FC:enable='between(t,32.4,41.0)',
drawtext=fontfile='$font':text='Saida para simuladores':x=72:y=936:fontsize=58:fontcolor=white:enable='between(t,41.0,49.4)',
drawtext=fontfile='$font':text='FreeTrack, TrackIR compativel e Mouse Look':x=72:y=1004:fontsize=32:fontcolor=0xD7F9FC:enable='between(t,41.0,49.4)',
drawtext=fontfile='$font':text='Pronto para rodar':x=72:y=936:fontsize=58:fontcolor=white:enable='between(t,49.4,59)',
drawtext=fontfile='$font':text='Pagamento unico de R$ 19,99 no site':x=72:y=1004:fontsize=32:fontcolor=0xD7F9FC:enable='between(t,49.4,59)',
fade=t=in:st=0:d=0.35,fade=t=out:st=58.35:d=0.65[vtext];
[vtext][logo]overlay=x=main_w-overlay_w-36:y=28:format=auto:shortest=1,format=yuv420p[outv];
[0:a]volume=0.23,afade=t=in:st=0:d=0.35,afade=t=out:st=58.35:d=0.65[orig];
[2:a]volume=0.68,afade=t=in:st=0:d=1.0,afade=t=out:st=57:d=2.0[music];
[orig][music]amix=inputs=2:duration=shortest:normalize=0,alimiter=limit=0.95[aout]
"@

    & ffmpeg `
        -hide_banner `
        -y `
        -i $transitioned `
        -loop 1 `
        -i $logo `
        -i $music `
        -t 59 `
        -filter_complex $filter `
        -map "[outv]" `
        -map "[aout]" `
        -c:v libx264 `
        -preset medium `
        -crf 20 `
        -r 30 `
        -c:a aac `
        -b:a 160k `
        -movflags +faststart `
        $Output

    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao gerar o video de apresentacao."
    }

    Write-Host "Video gerado em: $Output"
}
finally {
    if ((Test-Path -LiteralPath $workDir) -and ($env:TORVIX_KEEP_TEMP -ne "1")) {
        Remove-Item -LiteralPath $workDir -Recurse -Force
    }
}
