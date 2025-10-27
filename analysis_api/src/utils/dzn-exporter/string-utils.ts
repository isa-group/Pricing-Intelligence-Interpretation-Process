import { EOL } from 'os';
import { Chunk } from './index.js';

export function generateChunkBlock(chunks: Chunk[]): string {
  const result = [];
  for (let i = 0; i < chunks.length; i++) {
    result.push(generateChunk(chunks[i]));
  }

  return result.join('');
}

export function generateChunk(chunk: Chunk) {
  let rightValue = chunk.value;

  if (chunk.row && chunk.col) {
    rightValue =
      `array2d(${chunk.row.toUpperCase()}, ${chunk.col.toUpperCase()}, [${EOL}` +
      chunk.value +
      '])';
  }

  return `${chunk.left} = ${rightValue};` + EOL;
}

export function formatMatrixToString(target: string[], dataMatrix: number[][]): string {
  let dataString = '';

  if (dataMatrix.length === 0) {
    return dataString;
  }

  if (dataMatrix.length != target.length) {
    throw Error('Names array has to be equal to the number of rows of the matrix');
  }

  const padding = '    ';

  for (let i = 0; i < dataMatrix.length; i++) {
    dataString = dataString.concat(padding, `% ${target[i]}`, EOL);
    let matrixDataString = dataMatrix[i].join(',').concat(',', EOL);

    if (i === dataMatrix.length - 1) {
      matrixDataString = dataMatrix[i].join(',').concat(EOL);
    }

    dataString = dataString.concat(padding, matrixDataString);
  }
  return dataString;
}
