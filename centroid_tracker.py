from scipy.spatial import distance as dist
from collections import OrderedDict
import numpy as np
import uuid


def get_centroid(object_rect):
	start_x, start_y, w, h = object_rect

	end_x = start_x + w
	end_y = start_y + h

	c_x = int((start_x + end_x) / 2.0)
	c_y = int((start_y + end_y) / 2.0)

	return c_x, c_y


class CentroidTracker:
	def __init__(self, max_disappeared=50):
		self.next_object_id = str(uuid.uuid4())
		self.objects = OrderedDict()
		self.disappeared = OrderedDict()

		self.max_disappeared = max_disappeared

	def register(self, object):
		self.objects[self.next_object_id] = object
		self.disappeared[self.next_object_id] = 0
		self.next_object_id = str(uuid.uuid4())

	def unregister(self, object_id):
		del self.objects[object_id]
		del self.disappeared[object_id]

	def update(self, rects):
		if len(rects) == 0:

			for object_id in list(self.disappeared.keys()):
				self.disappeared[object_id] += 1
				if self.disappeared[object_id] > self.max_disappeared:
					self.unregister(object_id)

			return self.objects

		# if we are currently not tracking any objects take the input
		# centroids and register each of them
		if len(self.objects) == 0:
			for i in range(0, len(rects)):
				self.register(rects[i])

		# otherwise, we are currently tracking objects so we need to
		# try to match the input centroids to existing object
		# centroids
		else:
			# grab the set of object IDs and corresponding centroids
			object_ids = list(self.objects.keys())
			objects = list(self.objects.values())
			# compute the distance between each pair of object
			# centroids and input centroids, respectively -- our
			# goal will be to match an input centroid to an existing
			# object centroid
			# D = dist.cdist(np.array(object_centroids), input_centroids)

			D = dist.cdist(np.array(list(map(lambda  e: get_centroid(e), objects))),
										 np.array(list(map(lambda e: get_centroid(e), rects))))

			# in order to perform this matching we must (1) find the
			# smallest value in each row and then (2) sort the row
			# indexes based on their minimum values so that the row
			# with the smallest value is at the *front* of the index
			# list
			rows = D.min(axis=1).argsort()
			# next, we perform a similar process on the columns by
			# finding the smallest value in each column and then
			# sorting using the previously computed row index list
			cols = D.argmin(axis=1)[rows]

			# in order to determine if we need to update, register,
			# or deregister an object we need to keep track of which
			# of the rows and column indexes we have already examined
			used_rows = set()
			used_cols = set()
			# loop over the combination of the (row, column) index
			# tuples
			for (row, col) in zip(rows, cols):
				# if we have already examined either the row or
				# column value before, ignore it
				# val
				if row in used_rows or col in used_cols:
					continue
				# otherwise, grab the object ID for the current row,
				# set its new centroid, and reset the disappeared
				# counter
				object_id = object_ids[row]
				self.objects[object_id] = rects[col]
				self.disappeared[object_id] = 0
				# indicate that we have examined each of the row and
				# column indexes, respectively
				used_rows.add(row)
				used_cols.add(col)

			# compute both the row and column index we have NOT yet
			# examined
			unused_rows = set(range(0, D.shape[0])).difference(used_rows)
			unused_cols = set(range(0, D.shape[1])).difference(used_cols)

			# in the event that the number of object centroids is
			# equal or greater than the number of input centroids
			# we need to check and see if some of these objects have
			# potentially disappeared
			if D.shape[0] >= D.shape[1]:
				# loop over the unused row indexes
				for row in unused_rows:
					# grab the object ID for the corresponding row
					# index and increment the disappeared counter
					object_id = object_ids[row]
					self.disappeared[object_id] += 1
					# check to see if the number of consecutive
					# frames the object has been marked "disappeared"
					# for warrants unregistering the object
					if self.disappeared[object_id] > self.max_disappeared:
						self.unregister(object_id)

			# otherwise, if the number of input centroids is greater
			# than the number of existing object centroids we need to
			# register each new input centroid as a trackable object
			else:
				for col in unused_cols:
					self.register(rects[col])
		# return the set of trackable objects
		return self.objects
