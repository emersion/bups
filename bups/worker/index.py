#!/usr/bin/env python

import sys, stat, time, os, errno, re
from bup import metadata, options, git, index, drecurse, hlinkdb
from bup.helpers import *
from bup.hashsplit import GIT_MODE_TREE, GIT_MODE_FILE

from options import OptionsDict

def call_index(dirpath, optDict={}, callbacks={}):
    opt = OptionsDict(optDict)

    if "onread" in callbacks:
        progress = callbacks["onread"]
        log = callbacks["onread"]

    class IterHelper:
        def __init__(self, l):
            self.i = iter(l)
            self.cur = None
            self.next()

        def next(self):
            try:
                self.cur = self.i.next()
            except StopIteration:
                self.cur = None
            return self.cur


    def check_index(reader):
        try:
            log('check: checking forward iteration...\n')
            e = None
            d = {}
            for e in reader.forward_iter():
                if e.children_n:
                    if opt.verbose:
                        log('%08x+%-4d %r\n' % (e.children_ofs, e.children_n,
                                                e.name))
                    assert(e.children_ofs)
                    assert(e.name.endswith('/'))
                    assert(not d.get(e.children_ofs))
                    d[e.children_ofs] = 1
                if e.flags & index.IX_HASHVALID:
                    assert(e.sha != index.EMPTY_SHA)
                    assert(e.gitmode)
            assert(not e or e.name == '/')  # last entry is *always* /
            log('check: checking normal iteration...\n')
            last = None
            for e in reader:
                if last:
                    assert(last > e.name)
                last = e.name
        except:
            log('index error! at %r\n' % e)
            raise
        log('check: passed.\n')


    def clear_index(indexfile):
        indexfiles = [indexfile, indexfile + '.meta', indexfile + '.hlink']
        for indexfile in indexfiles:
            path = git.repo(indexfile)
            try:
                os.remove(path)
                if opt.verbose:
                    log('clear: removed %s\n' % path)
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise


    def update_index(top, excluded_paths, exclude_rxs):
        # tmax and start must be epoch nanoseconds.
        tmax = (time.time() - 1) * 10**9
        ri = index.Reader(indexfile)
        msw = index.MetaStoreWriter(indexfile + '.meta')
        wi = index.Writer(indexfile, msw, tmax)
        rig = IterHelper(ri.iter(name=top))
        tstart = int(time.time()) * 10**9

        hlinks = hlinkdb.HLinkDB(indexfile + '.hlink')

        hashgen = None
        if opt.fake_valid:
            def hashgen(name):
                return (GIT_MODE_FILE, index.FAKE_SHA)

        total = 0
        bup_dir = os.path.abspath(git.repo())
        index_start = time.time()
        for (path,pst) in drecurse.recursive_dirlist([top], xdev=opt.xdev,
                                                     bup_dir=bup_dir,
                                                     excluded_paths=excluded_paths,
                                                     exclude_rxs=exclude_rxs):
            if opt.verbose>=2 or (opt.verbose==1 and stat.S_ISDIR(pst.st_mode)):
                sys.stdout.write('%s\n' % path)
                sys.stdout.flush()
                elapsed = time.time() - index_start
                paths_per_sec = total / elapsed if elapsed else 0
                qprogress('Indexing: %d (%d paths/s)\r' % (total, paths_per_sec))
                if "onprogress" in callbacks:
                    callbacks["onprogress"]({
                        "type": "index",
                        "files_done": total,
                        "speed": str(int(paths_per_sec))+" paths/s"
                    })
            elif not (total % 128):
                elapsed = time.time() - index_start
                paths_per_sec = total / elapsed if elapsed else 0
                qprogress('Indexing: %d (%d paths/s)\r' % (total, paths_per_sec))
                if "onprogress" in callbacks:
                    callbacks["onprogress"]({
                        "type": "index",
                        "files_done": total,
                        "speed": str(int(paths_per_sec))+" paths/s"
                    })
            total += 1
            while rig.cur and rig.cur.name > path:  # deleted paths
                if rig.cur.exists():
                    rig.cur.set_deleted()
                    rig.cur.repack()
                    if rig.cur.nlink > 1 and not stat.S_ISDIR(rig.cur.mode):
                        hlinks.del_path(rig.cur.name)
                rig.next()
            if rig.cur and rig.cur.name == path:    # paths that already existed
                try:
                    meta = metadata.from_path(path, statinfo=pst)
                except (OSError, IOError), e:
                    add_error(e)
                    rig.next()
                    continue
                if not stat.S_ISDIR(rig.cur.mode) and rig.cur.nlink > 1:
                    hlinks.del_path(rig.cur.name)
                if not stat.S_ISDIR(pst.st_mode) and pst.st_nlink > 1:
                    hlinks.add_path(path, pst.st_dev, pst.st_ino)
                # Clear these so they don't bloat the store -- they're
                # already in the index (since they vary a lot and they're
                # fixed length).  If you've noticed "tmax", you might
                # wonder why it's OK to do this, since that code may
                # adjust (mangle) the index mtime and ctime -- producing
                # fake values which must not end up in a .bupm.  However,
                # it looks like that shouldn't be possible:  (1) When
                # "save" validates the index entry, it always reads the
                # metadata from the filesytem. (2) Metadata is only
                # read/used from the index if hashvalid is true. (3) index
                # always invalidates "faked" entries, because "old != new"
                # in from_stat().
                meta.ctime = meta.mtime = meta.atime = 0
                meta_ofs = msw.store(meta)
                rig.cur.from_stat(pst, meta_ofs, tstart,
                                  check_device=opt.check_device)
                if not (rig.cur.flags & index.IX_HASHVALID):
                    if hashgen:
                        (rig.cur.gitmode, rig.cur.sha) = hashgen(path)
                        rig.cur.flags |= index.IX_HASHVALID
                if opt.fake_invalid:
                    rig.cur.invalidate()
                rig.cur.repack()
                rig.next()
            else:  # new paths
                try:
                    meta = metadata.from_path(path, statinfo=pst)
                except (OSError, IOError), e:
                    add_error(e)
                    continue
                # See same assignment to 0, above, for rationale.
                meta.atime = meta.mtime = meta.ctime = 0
                meta_ofs = msw.store(meta)
                wi.add(path, pst, meta_ofs, hashgen = hashgen)
                if not stat.S_ISDIR(pst.st_mode) and pst.st_nlink > 1:
                    hlinks.add_path(path, pst.st_dev, pst.st_ino)

        elapsed = time.time() - index_start
        paths_per_sec = total / elapsed if elapsed else 0
        progress('Indexing: %d, done (%d paths/s).\n' % (total, paths_per_sec))
        if "onprogress" in callbacks:
            callbacks["onprogress"]({
                "type": "index",
                "files_done": total,
                "files_total": total,
                "speed": str(int(paths_per_sec))+" paths/s"
            })

        hlinks.prepare_save()

        if ri.exists():
            ri.save()
            wi.flush()
            if wi.count:
                wr = wi.new_reader()
                if opt.check:
                    log('check: before merging: oldfile\n')
                    check_index(ri)
                    log('check: before merging: newfile\n')
                    check_index(wr)
                mi = index.Writer(indexfile, msw, tmax)

                for e in index.merge(ri, wr):
                    # FIXME: shouldn't we remove deleted entries eventually?  When?
                    mi.add_ixentry(e)

                ri.close()
                mi.close()
                wr.close()
            wi.abort()
        else:
            wi.close()

        msw.close()
        hlinks.commit_save()

    def parse_excludes(opt): # See https://github.com/bup/bup/blob/master/lib/bup/helpers.py#L838
        return sorted(frozenset([realpath(x) for x in (opt.exclude_paths or [])]))
    def parse_rx_excludes(opt): # See https://github.com/bup/bup/blob/master/lib/bup/helpers.py#L859
        excluded_patterns = []
        for x in (opt.exclude_rxs or []):
            try:
                excluded_patterns.append(re.compile(x))
            except re.error, ex:
                raise Exception('invalid --exclude-rx pattern (%s): %s' % (x, ex))
        return excluded_patterns

    git.check_repo_or_die()
    indexfile = git.repo('bupindex')
    update_index(dirpath, parse_excludes(opt), parse_rx_excludes(opt))