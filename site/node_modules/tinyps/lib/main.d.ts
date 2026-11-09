import { type ProcessInfo } from './parse.js';
export type { ProcessInfo };
export type ProcessTree = Map<number, number[]>;
export type Protocol = 'tcp' | 'udp';
export declare function killTree(pid: number, signal?: NodeJS.Signals): Promise<void>;
export declare function listProcesses(): Promise<ProcessInfo[]>;
export declare function getProcessInfo(pid: number): Promise<ProcessInfo | undefined>;
export declare function findProcessesByName(name: string, options?: {
    loose?: boolean;
}): Promise<ProcessInfo[]>;
export declare function findProcessesByPort(port: number, options?: {
    protocol?: Protocol;
}): Promise<ProcessInfo[]>;
export declare function getProcessTree(pid: number): Promise<ProcessTree>;
export declare function isRunning(pid: number): boolean;
export declare function getDescendants(pid: number): Promise<number[]>;
export declare function getProcessAncestry(pid?: number): Promise<ProcessInfo[]>;
