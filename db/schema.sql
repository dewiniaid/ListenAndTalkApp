DROP SCHEMA IF EXISTS listenandtalk CASCADE;

CREATE SCHEMA listenandtalk;
SET search_path=listenandtalk,public;


CREATE TABLE student (
	id SERIAL NOT NULL,
	name_first VARCHAR NOT NULL,
	name_last VARCHAR NOT NULL,

	date_inactive TIMESTAMP WITH TIME ZONE NULL,  -- if non-NULL, this student is "deleted"; date is for future use in case we want to purge records from X years ago.
	date_created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
	PRIMARY KEY(id)
);
CREATE INDEX ON student(name_first, name_last);


CREATE TABLE staff (
	id SERIAL NOT NULL,
	name_first VARCHAR NOT NULL,
	name_last VARCHAR NOT NULL,

	date_inactive TIMESTAMP WITH TIME ZONE NULL,  -- if non-NULL, this student is "deleted"; date is for future use in case we want to purge records from X years ago.
	date_created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

	can_login BOOLEAN NOT NULL DEFAULT TRUE,	-- Don't allow teachers without this to login
	email VARCHAR NULL,

	last_visited TIMESTAMP WITH TIME ZONE,
	last_ip INET NULL,

	-- Teacher email address for OAuth login.
	-- TODO: Accounts, which might potentially need to be its own table.
	-- If using OAuth, this may just be an email address
	PRIMARY KEY(id),
	UNIQUE(email)
);
CREATE INDEX ON staff(name_first, name_last);
CREATE INDEX ON staff(email);


CREATE TABLE location (
	-- Lookup table of physical locations 
	id SERIAL NOT NULL,
	name TEXT NOT NULL,

	PRIMARY KEY (id),
	UNIQUE (name)
);
CREATE INDEX ON location(name);



CREATE TABLE category (
	-- Lookup table for types of activities
	id SERIAL NOT NULL,
	name TEXT NOT NULL,

	PRIMARY KEY (id),
	UNIQUE (name)
);
CREATE INDEX ON category(name);



CREATE TABLE attendance_status (
	-- Lookup table of attendance statuses (e.g. Present, Absent, Illness, Not Expected (as a drop-in feature)
	-- May want some additional metadata to simplify any reporting.
	id SERIAL NOT NULL,
	name TEXT NOT NULL,
	
	PRIMARY KEY (id),
	UNIQUE (name)
);
CREATE INDEX ON attendance_status(name);



CREATE TABLE activity (  -- Sometimes also called a "Roster"
	id SERIAL NOT NULL,
	name TEXT NOT NULL,

	staff_id INT NOT NULL,
	location_id INT NOT NULL,
	category_id INT NOT NULL,
	
	-- TODO: Track when this class is (so we know when the rostering information is useful)
	start_date DATE NOT NULL, -- First possible date of this class
	end_date DATE NOT NULL,	-- Last possible date of this class.

	-- start_time TIME NOT NULL, --- 
	-- end_time TIME NOT NULL,

	-- date_range DATERANGE NOT NULL, 
	-- PostgreSQL has some built-in capabilities for handling ranges more efficiently, but this may be overkill.
	-- I usually maintain this field for efficient querying, but have it updated by trigger -- so backend only
	-- needs to reference it (and the slightly arcane syntax) when it's useful to do so.
	
	-- activity behavior options
	-- default_attendance_status_id INT NULL,  -- For special classes where we want a particular attendance status to be the default assumption.
	allow_dropins BOOLEAN NOT NULL DEFAULT FALSE,	-- "Drop-in" classes don't maintain a roster, but instead allow an ad-hoc selection 
	-- of a particular student + attendance status.
	
	date_inactive TIMESTAMP WITH TIME ZONE NULL,  -- if non-NULL, this activity is "deleted"; date is for future use in case we want to purge records from X years ago.
	date_created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

	PRIMARY KEY(id),
	FOREIGN KEY(staff_id) REFERENCES staff(id) ON UPDATE CASCADE ON DELETE RESTRICT,
	FOREIGN KEY(location_id) REFERENCES location(id) ON UPDATE CASCADE ON DELETE RESTRICT,
	FOREIGN KEY(category_id) REFERENCES category(id) ON UPDATE CASCADE ON DELETE RESTRICT
--	FOREIGN KEY(default_attendance_status_id) REFERENCES attendance_status(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX ON activity(staff_id);
CREATE INDEX ON activity(location_id);
CREATE INDEX ON activity(category_id);



CREATE TABLE activity_enrollment (
	-- The set of all activity_enrollment records for a given activity overlapping today's date is the roster for today.
	-- (SELECT ... FROM activity_enrollment WHERE ... AND ('now' BETWEEN start_time AND end_time) 
	id SERIAL NOT NULL,
	activity_id INT NOT NULL,
	student_id INT NOT NULL,
	start_date DATE NOT NULL,
	end_date DATE NULL,
		
	PRIMARY KEY(id),
	FOREIGN KEY(activity_id) REFERENCES activity(id) ON UPDATE CASCADE ON DELETE CASCADE,
	FOREIGN KEY(student_id) REFERENCES student(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE INDEX ON activity_enrollment(activity_id, student_id);
CREATE INDEX ON activity_enrollment(student_id);



CREATE TABLE attendance ( -- aka "Checkin"
	-- NOTE: This system does not currently handle any notion of multiple checkins in a particular class per day
	-- This may or may not matter, we should discuss this.
	-- (If a student leaves a class partway through to go to another class, and then returns, should they be re-checked-in?)
	
	-- ASSUMPTIONS: (old)
	-- An attendance entry is expected for a class for a particular day if all of the below conditions are met:
	-- a) The class meets on that day
	-- b) The student's enrollment in the class overlaps the class time
	
	-- A student MAY have an attendance entry for a class, even if the above conditions are not met.  This can happen if
	-- a) It's a drop-in class, and the student is a drop-in.
	-- b) Attendance was entered, but then the student was dropped.  (e.g. a prearranged absence in the future.)
	--
	-- In the case of a), we probably want to still include this record on any reporting.
	-- In the case of b), we probably don't want to include this record because we don't care if a student was going to be 
	-- ... on vacation next week if they're no longer attending.
	student_id INT NOT NULL,
	activity_id INT NOT NULL,
	date DATE NOT NULL,
	status_id INT NOT NULL,
	comment TEXT NULL, -- Optional
	date_entered TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
	PRIMARY KEY(student_id, activity_id, date),
	FOREIGN KEY(student_id) REFERENCES student(id) ON UPDATE CASCADE ON DELETE CASCADE,
	FOREIGN KEY(activity_id) REFERENCES activity(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE VIEW attendance_upsert AS SELECT * FROM attendance;
CREATE OR REPLACE FUNCTION attendance_upsert_tproc()
RETURNS TRIGGER
SECURITY INVOKER
VOLATILE
LANGUAGE PLPGSQL
AS $PROC$
BEGIN
	LOOP
		-- Try an update first
		UPDATE attendance 
		SET
			status_id=NEW.status_id,
			comment=NEW.comment,
			date_entered=COALESCE(NEW.date_entered, 'now')
		WHERE
			student_id=NEW.student_id AND activity_id=NEW.activity_id AND date=NEW.date
		;

		IF FOUND THEN
			-- Update found something, so we're done here.
			RETURN NEW;
		END IF;

		-- Update affected 0 rows, so try an insert instead.
		BEGIN
			INSERT INTO attendance (student_id, activity_id, date, status_id, comment, date_entered)
			VALUES (NEW.student_id, NEW.activity_id, NEW.date, NEW.status_id, NEW.comment, COALESCE(NEW.date_entered, 'now'));
			RETURN NEW;
		EXCEPTION WHEN unique_violation THEN
			-- Record already exists due to concurrent update.  Retry update by looping again.
		END;
	END LOOP;
END;	
$PROC$;
CREATE TRIGGER attendance_upsert_insert INSTEAD OF INSERT ON attendance_upsert FOR EACH ROW EXECUTE PROCEDURE attendance_upsert_tproc();


CREATE TABLE attendance_history (
	-- Archive of past attendance data for future development/reporting.
	id SERIAL NOT NULL,
	student_id INT NOT NULL,
	activity_id INT NOT NULL,
	date DATE NOT NULL,
	status_id INT NOT NULL,
	comment TEXT NULL, -- Optional
	date_entered TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
	PRIMARY KEY(id),
	FOREIGN KEY(student_id) REFERENCES student(id) ON UPDATE CASCADE ON DELETE CASCADE,
	FOREIGN KEY(activity_id) REFERENCES activity(id) ON UPDATE CASCADE ON DELETE CASCADE
);
CREATE OR REPLACE FUNCTION attendance_maintain_history_tproc()
RETURNS TRIGGER
SECURITY INVOKER
VOLATILE
LANGUAGE PLPGSQL
AS $PROC$
BEGIN
	IF TG_OP='UPDATE' THEN
		IF ROW(NEW.*) IS NOT DISTINCT FROM ROW(OLD.*) THEN
			RETURN NEW;	-- Nothing changed!
		END IF;
	END IF;
	
	INSERT INTO attendance_history (student_id, activity_id, date, status_id, comment, date_entered)
	VALUES (OLD.student_id, OLD.activity_id, OLD.date, OLD.status_id, OLD.comment, OLD.date_entered);
	IF TG_OP='UPDATE' THEN
		RETURN NEW;
	END IF;
	RETURN OLD;
END
$PROC$;
CREATE TRIGGER attendance_maintain_history AFTER UPDATE OR DELETE ON attendance FOR EACH ROW EXECUTE PROCEDURE attendance_maintain_history_tproc();



GRANT ALL PRIVILEGES ON SCHEMA listenandtalk TO backend;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA listenandtalk TO backend;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA listenandtalk TO backend;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA listenandtalk TO backend;