#version 330 core

uniform sampler2D PygameTexture;
uniform float Time;

// Base shader variables
in vec2 FragCoord;
out vec4 FragColor;

//const vec4 LightColorBright = vec4(1.0, 0.6, 0.2, 0.0);
const vec4 LightColorDark = vec4(0.52, 0.36, 0.2, 0.0);

const float Curvature = 0.3;
const float ReflectionBlurItterations = 10.0;
const float ReflectionBlurSize = 0.25;

float Random(vec2 Seed)
{
    return fract(sin(dot((Seed * (mod(Time, 1.0) + 1.0)), vec2(11.9898, 78.233))) * 43758.5453);
}

vec2 CurveUVs(vec2 UV)
{
    vec2 Multiplier = abs(UV * Curvature);
    vec2 ScaledUV = UV * (pow(Multiplier, vec2(2.5)) + 1.0).yx;
    float MaxValue = max(abs(ScaledUV.x), abs(ScaledUV.y));
    
    if (MaxValue > 1.0)
        return vec2(-min(1.0, (MaxValue - 1.0) * 15.0));
    else
        return ScaledUV * 0.5 + 0.5;
}

vec3 InsetUV(vec2 UV, float Inset)
{
    vec2 ClampedUV = clamp(UV, vec2(Inset), vec2(1.0 - Inset));
    vec2 RemmapedUV = (UV - Inset) / (1.0 - 2.0 * Inset);
    
    float Smoothing = 0.01;
    vec2 Centered = abs(RemmapedUV - 0.5) - 0.5;
    float IsInside = Smoothing - clamp(max(Centered.x, Centered.y), 0.0, Smoothing);
    
    return vec3(clamp(RemmapedUV, 0.0, 1.0), mix(0.0, 1.0, IsInside / Smoothing));
}

vec4 CompressColor(vec4 Color, float Amount)
{
    // Calculate the average of the color components
    float Average = (Color.r + Color.g + Color.b) / 3.0;
    
    // Interpolate between the original color and the average (white point)
    return mix(Color, vec4(Average), Amount);
}

void main()
{
    // Center pixel coordinates (from -1 to 1)
    vec2 CenteredUV = FragCoord * 2.0 - 1.0;
    
    // Curved pixel coordinates for the screen effects
    vec2 ScreenUV = CurveUVs(CenteredUV * 1.05);
    
    FragColor = vec4(0.0);
    
    // Outside the screen
    if (ScreenUV.x < 0.0)
    {
        // Set ambient color
        FragColor += vec4(0.8, 0.8, 0.8, 0.0) * 0.2;
        
        // Light reflection
	    for(float i = 0.0; i < ReflectionBlurItterations; i++)
	    {
	    	vec2 ReflectionUV = FragCoord + (vec2(Random(FragCoord.xy + i), Random(FragCoord.yx + i)) - 0.5) * ReflectionBlurSize;
	    	FragColor += texture(PygameTexture, clamp(ReflectionUV, 0.0, 1.0)) / ReflectionBlurItterations;
	    }
        
        FragColor *= -ScreenUV.x;
    }
    
    // Inside the screen
    else
    {
        // Screen effect //////////////////////////////////////////////////////////////////////////////////
        
        // Noise in background
        float Noise = 0.1 * (Random(ScreenUV) - 0.5);

        // Large scane line effect
        float ScanPosition = 1.0 - mod(Time / 5.0, 2.0);
        float DistToScan = 1.0 - (ScreenUV.y - ScanPosition) * 4.0;
        vec4 ScreenScan = (DistToScan > 0.0 && DistToScan < 1.0) ? CompressColor(LightColorDark, 0.5) * 0.075 * DistToScan : vec4(0.0);

        // Backlighting from screen
        float Backlighting = max(0.0, 2.65 - length((ScreenUV * 2.0 - 1.0) / 0.5));
        Backlighting = mix(0.0, 0.5, Backlighting / 2.65);
        
        // Fade screen at its edges
        vec2 Temp = abs(ScreenUV - 0.5);
        float ScreenBorder = 1.0 - max(0.0, max(Temp.x, Temp.y) - 0.485) / 0.015;
    
        // Apply scan line effect + lighting specular and diffuse + back lighting from screen
        FragColor += (Noise + ScreenScan) + (Backlighting * LightColorDark);
        
        // Text rendering /////////////////////////////////////////////////////////////////////////////////
        
        vec3 TextSampleUV = InsetUV(ScreenUV, 0.025);
        
        // The text itself
        FragColor += texture(PygameTexture, TextSampleUV.xy) * (TextSampleUV.z < 1.0 ? 0.0 : 1.0);
        
        // Bloom using composed MipMaps
	    FragColor += (textureLod(PygameTexture, TextSampleUV.xy, 3.0) +
                      textureLod(PygameTexture, TextSampleUV.xy, 4.0) +
                      textureLod(PygameTexture, TextSampleUV.xy, 5.0)) * TextSampleUV.z * 0.35;
                        
        FragColor *= ScreenBorder;
    }
}
