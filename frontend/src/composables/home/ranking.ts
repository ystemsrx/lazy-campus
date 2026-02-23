import type { Task, WorkerProfile } from '../../types/api'
import type { HomeTaskSort, HomeWorkerSort } from './model'
import { parseUTC } from '../../utils/time'

function toTimestamp(iso: string): number {
  return parseUTC(iso).getTime()
}

function createdAtDesc(a: Task, b: Task): number {
  return toTimestamp(b.created_at) - toTimestamp(a.created_at)
}

function taskPublisherRatingFormula(task: Task) {
  return {
    avg: task.publisher_rating_avg,
    count: task.publisher_rating_count,
  }
}

function taskPublisherCompletedFormula(task: Task) {
  return task.publisher_completed_count ?? 0
}

function workerRatingFormula(worker: WorkerProfile) {
  return {
    avg: worker.overall_rating_avg,
    count: worker.overall_rating_count,
    completed: worker.worker_completed_count,
  }
}

function compareTaskByDeadlineAsc(a: Task, b: Task): number {
  if (!a.deadline && !b.deadline) return createdAtDesc(a, b)
  if (!a.deadline) return 1
  if (!b.deadline) return -1
  return toTimestamp(a.deadline) - toTimestamp(b.deadline)
}

function compareTaskByPublisherRating(a: Task, b: Task): number {
  const aRating = taskPublisherRatingFormula(a)
  const bRating = taskPublisherRatingFormula(b)
  return (
    bRating.avg - aRating.avg ||
    bRating.count - aRating.count ||
    createdAtDesc(a, b)
  )
}

function compareTaskByPublisherCompleted(a: Task, b: Task): number {
  return (
    taskPublisherCompletedFormula(b) - taskPublisherCompletedFormula(a) ||
    createdAtDesc(a, b)
  )
}

function compareTaskByPriceDesc(a: Task, b: Task): number {
  return b.price - a.price || createdAtDesc(a, b)
}

function compareWorkerByRating(a: WorkerProfile, b: WorkerProfile): number {
  const aRating = workerRatingFormula(a)
  const bRating = workerRatingFormula(b)
  return (
    bRating.avg - aRating.avg ||
    bRating.count - aRating.count ||
    bRating.completed - aRating.completed
  )
}

function compareWorkerByCompleted(a: WorkerProfile, b: WorkerProfile): number {
  const aRating = workerRatingFormula(a)
  const bRating = workerRatingFormula(b)
  return (
    bRating.completed - aRating.completed ||
    bRating.avg - aRating.avg ||
    bRating.count - aRating.count
  )
}

export function sortTasksByMode(tasks: Task[], sort: HomeTaskSort): Task[] {
  const result = [...tasks]
  if (sort === 'newest') {
    result.sort(createdAtDesc)
  } else if (sort === 'deadline_asc') {
    result.sort(compareTaskByDeadlineAsc)
  } else if (sort === 'publisher_rating') {
    result.sort(compareTaskByPublisherRating)
  } else if (sort === 'publisher_completed') {
    result.sort(compareTaskByPublisherCompleted)
  } else if (sort === 'price_desc') {
    result.sort(compareTaskByPriceDesc)
  }
  return result
}

export function sortWorkersByMode(workers: WorkerProfile[], sort: HomeWorkerSort): WorkerProfile[] {
  const result = [...workers]
  if (sort === 'worker_rating') {
    result.sort(compareWorkerByRating)
  } else if (sort === 'worker_completed') {
    result.sort(compareWorkerByCompleted)
  }
  return result
}
