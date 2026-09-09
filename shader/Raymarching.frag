#version 300 es
precision highp float;

uniform vec2      uResolution;
uniform sampler2D uChannel0;
uniform float     uChannelTime;

out vec4 fragColor;

float sdPlane(vec3 p) {
    float width  = .4;
    float tiling = 15.;

    vec2 idx = floor(p.xy * tiling);
    vec2 str = vec2(uResolution.y / uResolution.x, 1.);
    float h = length(texture(uChannel0, str * idx / (2. * tiling) + .5).xyz) / 7.;

    vec2 f = fract(p.xy * tiling) - .5;
    float N = 4.;
    float l = pow(pow(abs(f.x), N) + pow(abs(f.y), N), 1. / N);

    return h * smoothstep(0., 0.05, width - l);
}

float castRay(vec3 ro, vec3 rd) {
    vec3 p = ro;
    float t = .05 * fract(sin(dot(rd, vec3(125.45, 213.345, 156.2001))));
    for (float d = .5; d < 2.4; d += .004) {
        p = ro + rd * (d + t);
        if (p.z < sdPlane(p)) break;
    }
    return p.z;
}

void main() {
    vec2 st = (2. * gl_FragCoord.xy - uResolution) / uResolution.y;

    vec3 ro = vec3(0., 0., 1.);
    vec3 rd = normalize(vec3(st, -1.));

    float d = castRay(ro, rd);
    fragColor = vec4(vec3(d) * 5., 1.);
}
