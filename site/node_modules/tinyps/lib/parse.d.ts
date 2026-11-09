export interface ProcessInfo {
    pid: number;
    ppid: number;
    name: string;
    command: string;
}
export declare function parsePsOutput(stdout: string): ProcessInfo[];
export declare function parseWin32ProcessJson(stdout: string): ProcessInfo[];
export declare function parseSsOutput(stdout: string): number[];
export declare function parseLsofOutput(stdout: string, port: number): number[];
export declare function parseOwningProcessJson(stdout: string): number[];
