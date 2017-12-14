#!/usr/bin/env python
"""
#
#------------------------------------------------------------------------------
#                         University of Minnesota
#         Copyright 2016, Regents of the University of Minnesota
#------------------------------------------------------------------------------
# Author:
#
#  James E Johnson
#
#------------------------------------------------------------------------------
"""

import sys
from Bio.Seq import reverse_complement, translate


def bed_from_line(line,ensembl=False):
    fields = line.rstrip('\r\n').split('\t')
    if len(fields) < 12:
        return None
    (chrom, chromStart, chromEnd, name, score, strand,
     thickStart, thickEnd, itemRgb,
     blockCount, blockSizes, blockStarts) = fields[0:12]
    bed_entry = BedEntry(chrom=chrom, chromStart=chromStart, chromEnd=chromEnd,
                         name=name, score=score, strand=strand,
                         thickStart=thickStart, thickEnd=thickEnd,
                         itemRgb=itemRgb,
                         blockCount=blockCount,
                         blockSizes=blockSizes.rstrip(','),
                         blockStarts=blockStarts.rstrip(','))
    if ensembl and len(fields) >= 20:
        bed_entry.second_name = fields[12]
        bed_entry.cds_start_status = fields[13]
        bed_entry.cds_end_status = fields[14]
        bed_entry.exon_frames = fields[15].rstrip(',')
        bed_entry.biotype = fields[16]
        bed_entry.gene_name = fields[17]
        bed_entry.second_gene_name = fields[18]
        bed_entry.gene_type = fields[19]
    return bed_entry



class BedEntry( object ):
    def __init__(self, chrom=None, chromStart=None, chromEnd=None,
                 name=None, score=None, strand=None,
                 thickStart=None, thickEnd=None, itemRgb=None,
                 blockCount=None, blockSizes=None, blockStarts=None):
        self.chrom = chrom
        self.chromStart = int(chromStart)
        self.chromEnd = int(chromEnd)
        self.name = name
        self.score = int(score) if score is not None else 0
        self.strand = '-' if str(strand).startswith('-') else '+'
        self.thickStart = int(thickStart) if thickStart else self.chromStart
        self.thickEnd = int(thickEnd) if thickEnd else self.chromEnd
        self.itemRgb = str(itemRgb) if itemRgb is not None else r'100,100,100'
        self.blockCount = int(blockCount)
        if isinstance(blockSizes, str) or isinstance(blockSizes, unicode):
            self.blockSizes = [int(x) for x in blockSizes.split(',')]
        elif isinstance(blockSizes, list):
            self.blockSizes = [int(x) for x in blockSizes]
        else:
            self.blockSizes = blockSizes
        if isinstance(blockStarts, str) or isinstance(blockSizes, unicode):
            self.blockStarts = [int(x) for x in blockStarts.split(',')]
        elif isinstance(blockStarts, list):
            self.blockStarts = [int(x) for x in blockStarts]
        else:
            self.blockStarts = blockStarts
        self.second_name = None
        self.cds_start_status = None
        self.cds_end_status = None
        self.exon_frames = None
        self.biotype = None
        self.gene_name = None
        self.second_gene_name = None
        self.gene_type = None
        self.seq = None
        self.cdna = None
        self.pep = None
        # T26C
        self.aa_change = []
        # p.Trp26Cys g.<pos><ref>><alt> # g.1304573A>G
        self.variants = []


    def __str__(self):
        return '%s\t%d\t%d\t%s\t%d\t%s\t%d\t%d\t%s\t%d\t%s\t%s' % (
            self.chrom, self.chromStart, self.chromEnd,
            self.name, self.score, self.strand,
            self.thickStart, self.thickEnd, str(self.itemRgb), self.blockCount,
            ','.join([str(x) for x in self.blockSizes]),
            ','.join([str(x) for x in self.blockStarts]))


    def get_splice_junctions(self):
        splice_juncs = []
        for i in range(self.blockCount  - 1):
            splice_junc = "%s:%d_%d" % (self.chrom, self.chromStart + self.blockSizes[i], self.chromStart + self.blockStarts[i+1])
            splice_juncs.append(splice_junc)
        return splice_juncs


    def get_exon_seqs(self):
        if not self.seq:
            return None
        exons = []
        for i in range(self.blockCount):
            # splice_junc = "%s:%d_%d" % (self.chrom, self.chromStart + self.blockSizes[i], self.chromStart + self.blockStarts[i+1])
            exons.append(self.seq[self.blockStarts[i]:self.blockStarts[i] + self.blockSizes[i]])
        if self.strand == '-':  #reverse complement
            exons.reverse()
            for i,s in enumerate(exons):
                exons[i] = reverse_complement(s)
        return exons


    def get_spliced_seq(self,strand=None):
        if not self.seq:
            return None
        seq = ''.join(self.get_exon_seqs())
        if strand and self.strand != strand:
            seq = reverse_complement(seq)
        return seq


    def get_cdna(self):
        if not self.cdna:
            self.cdna = self.get_spliced_seq()
        return self.cdna


    def get_cds(self):
        cdna = self.get_cdna()
        if cdna:
            if self.chromStart == self.thickStart and self.chromEnd == self.thickEnd:
                return cdna
            pos = [self.offset_of_pos(self.thickStart),self.offset_of_pos(self.thickEnd)] 
            if 0 <= min(pos) <= max(pos) <= len(cdna):
                return cdna[min(pos):max(pos)]
        return None


    def get_cigar(self): 
        cigar = ''
        md = ''
        r = range(self.blockCount)
        rev = self.strand == '-'
        ## if rev: r.reverse()
        xl = None
        for x in r:
            if xl is not None:
                intronSize = abs(self.blockStarts[x] - self.blockSizes[xl] - self.blockStarts[xl])
                cigar += '%dN' % intronSize
            cigar += '%dM' % self.blockSizes[x]
            xl = x
        return cigar


    def get_cigar_md(self): 
        cigar = ''
        md = ''
        r = range(self.blockCount)
        rev = self.strand == '-'
        ## if rev: r.reverse()
        xl = None
        for x in r:
            if xl is not None:
                intronSize = abs(self.blockStarts[x] - self.blockSizes[xl] - self.blockStarts[xl])
                cigar += '%dN' % intronSize
            cigar += '%dM' % self.blockSizes[x]
            xl = x
        md = '%d' % sum(self.blockSizes)
        return (cigar,md)


    def get_translation(self,sequence=None):
        translation = None
        seq = sequence if sequence else self.get_spliced_seq()
        if seq:
            seqlen = len(seq) / 3 * 3;
            if seqlen >= 3:
                translation = translate(seq[:seqlen])
        return translation


    def get_translations(self):
        translations = []
        seq = self.get_spliced_seq()
        if seq:
            for i in range(3):
                translation = self.get_translation(sequence=seq[i:])
                if translation:
                    translations.append(translation)
        return translations

    def pos_of_na(self, offset):
        if offset is not None and 0 <= offset < sum(self.blockSizes):
            r = range(self.blockCount)
            rev = self.strand == '-'
            if rev:
                r.reverse()
            nlen = 0
            for x in r:
                if offset < nlen + self.blockSizes[x]:
                    if rev:
                        return self.chromStart + self.blockStarts[x] + self.blockSizes[x] - (offset - nlen)
                    else: 
                        return self.chromStart + self.blockStarts[x] + (offset - nlen)
                nlen += self.blockSizes[x]
        return None

    def offset_of_pos(self, pos): 
        if not self.chromStart <= pos < self.chromEnd:
            return -1
        r = range(self.blockCount)
        rev = self.strand == '-'
        if rev:
            r.reverse()
        nlen = 0
        for x in r: 
            bStart = self.chromStart + self.blockStarts[x]
            bEnd = bStart + self.blockSizes[x]
            ## print >> sys.stdout, "offset_of_pos %d  %d  %d     %d" % (bStart,pos,bEnd,nlen)
            if bStart <= pos < bEnd:
                return nlen + (bEnd - pos if rev else pos - bStart)
            nlen += self.blockSizes[x]

    def apply_variant(self,pos,ref,alt):
        pos = int(pos)
        if not ref or not alt:
            print >> sys.stderr, "variant requires ref and alt sequences"
            return
        if not self.chromStart <= pos <= self.chromEnd:
            print >> sys.stderr, "variant not in entry %s: %s %d < %d < %d" % (self.name,self.strand, self.chromStart,pos,self.chromEnd)
            print >> sys.stderr, "%s" % str(self)
            return
        if len(ref) != len(alt):
            print >> sys.stderr, "variant only works for snp: %s  %s" % (ref,alt)
            return
        if not self.seq:
            print >> sys.stderr, "variant entry %s has no seq" % self.name
            return
        """
        if self.strand  == '-':
            ref = reverse_complement(ref)
            alt = reverse_complement(alt)
        """
        bases = list(self.seq)
        offset = pos - self.chromStart
        for i in range(len(ref)):
            # offset = self.offset_of_pos(pos+i)
            if offset is not None:
                bases[offset+i] = alt[i]
            else:
                print >> sys.stderr, "variant offset %s: %s %d < %d < %d" % (self.name,self.strand,self.chromStart,pos+1,self.chromEnd)
                print >> sys.stderr, "%s" % str(self)
        self.seq = ''.join(bases)
        self.variants.append("g.%d%s>%s" % (pos+1,ref,alt))

    def get_variant_bed(self,pos,ref,alt):
        pos = int(pos)
        if not ref or not alt:
            print >> sys.stderr, "variant requires ref and alt sequences"
            return None
        if not self.chromStart <= pos <= self.chromEnd:
            print >> sys.stderr, "variant not in entry %s: %s %d < %d < %d" % (self.name,self.strand, self.chromStart,pos,self.chromEnd)
            print >> sys.stderr, "%s" % str(self)
            return None
        if not self.seq:
            print >> sys.stderr, "variant entry %s has no seq" % self.name
            return None
        tbed = BedEntry(chrom = self.chrom, chromStart = self.chromStart, chromEnd = self.chromEnd,
                       name = self.name, score = self.score, strand = self.strand,
                       thickStart = self.chromStart, thickEnd = self.chromEnd, itemRgb = self.itemRgb,
                       blockCount = self.blockCount, blockSizes = self.blockSizes, blockStarts = self.blockStarts)
        bases = list(self.seq)
        offset = pos - self.chromStart
        tbed.seq = ''.join(bases[:offset] + list(alt) + bases[offset+len(ref):])
        if len(ref) != len(alt):
            diff = len(alt) - len(ref)
            rEnd = pos + len(ref)
            aEnd = pos + len(alt)
            #need to adjust blocks
            # change spans blocks, 
            for x in range(tbed.blockCount):
                bStart = tbed.chromStart + tbed.blockStarts[x]
                bEnd = bStart + tbed.blockSizes[x]
                # change within a block or extends (last block), adjust blocksize
                #  seq:            GGGcatGGG     
                #  ref c alt tag:  GGGtagatGGG  
                #  ref cat alt a:  GGGaGGG  
                if bStart <= pos < rEnd < bEnd:
                    tbed.blockSizes[x] += diff
        return tbed

    ## (start,end)
    def get_subrange(self,tstart,tstop,debug=False):
        chromStart = self.chromStart
        chromEnd = self.chromEnd
        if debug:
            print >> sys.stderr, "%s" % (str(self))
        r = range(self.blockCount)
        if self.strand == '-':
            r.reverse()
        bStart = 0
        bEnd = 0
        for x in r:
            bEnd = bStart + self.blockSizes[x]
            if bStart <= tstart < bEnd:
                if self.strand == '+':
                    chromStart = self.chromStart + self.blockStarts[x] +\
                        (tstart - bStart)
                else:
                    chromEnd = self.chromStart + self.blockStarts[x] +\
                        self.blockSizes[x] - (tstart - bStart)
            if bStart <= tstop < bEnd:
                if self.strand == '+':
                    chromEnd = self.chromStart + self.blockStarts[x] +\
                        (tstop - bStart)
                else:
                    chromStart = self.chromStart + self.blockStarts[x] +\
                        self.blockSizes[x] - (tstop - bStart)
            if debug:
                print >> sys.stderr,\
                    "%3d %s\t%d\t%d\t%d\t%d\t%d\t%d"\
                    % (x, self.strand, bStart, bEnd,
                       tstart, tstop, chromStart, chromEnd)
            bStart += self.blockSizes[x]
        return(chromStart, chromEnd)


    # get the blocks for sub range
    def get_blocks(self, chromStart, chromEnd):
        tblockCount = 0
        tblockSizes = []
        tblockStarts = []
        for x in range(self.blockCount):
            bStart = self.chromStart + self.blockStarts[x]
            bEnd = bStart + self.blockSizes[x]
            if bStart > chromEnd:
                break
            if bEnd < chromStart:
                continue
            cStart = max(chromStart, bStart)
            tblockStarts.append(cStart - chromStart)
            tblockSizes.append(min(chromEnd, bEnd) - cStart)
            tblockCount += 1
        return (tblockCount, tblockSizes, tblockStarts)


    def trim(self, tstart, tstop, debug=False):
        (tchromStart, tchromEnd) =\
            self.get_subrange(tstart, tstop, debug=debug)
        (tblockCount, tblockSizes, tblockStarts) =\
            self.get_blocks(tchromStart, tchromEnd)
        tbed = BedEntry(
            chrom=self.chrom, chromStart=tchromStart, chromEnd=tchromEnd,
            name=self.name, score=self.score, strand=self.strand,
            thickStart=tchromStart, thickEnd=tchromEnd, itemRgb=self.itemRgb,
            blockCount=tblockCount,
            blockSizes=tblockSizes, blockStarts=tblockStarts)
        if self.seq:
            ts = tchromStart-self.chromStart
            te = tchromEnd - tchromStart + ts
            tbed.seq = self.seq[ts:te]
        return tbed


    def get_filtered_translations(self,untrimmed=False,filtering=True,ignore_left_bp=0,ignore_right_bp=0,debug=False):
        translations = [None,None,None]
        seq = self.get_spliced_seq()
        ignore = (ignore_left_bp if self.strand == '+' else ignore_right_bp) / 3
        block_sum = sum(self.blockSizes)
        exon_sizes = [x for x in self.blockSizes]
        if self.strand == '-':
            exon_sizes.reverse()
        splice_sites = [sum(exon_sizes[:x]) / 3 for x in range(1,len(exon_sizes))]
        if debug:
            print >> sys.stderr, "splice_sites: %s" % splice_sites
        junc = splice_sites[0] if len(splice_sites) > 0 else exon_sizes[0]
        if seq:
            for i in range(3):
                translation = self.get_translation(sequence=seq[i:])
                if translation:
                    tstart = 0
                    tstop = len(translation)
                    offset = (block_sum - i) % 3
                    if debug:
                        print >> sys.stderr, "frame: %d\ttstart: %d  tstop: %d  offset: %d\t%s" % (i,tstart,tstop,offset,translation)
                    if not untrimmed:
                        tstart = translation.rfind('*',0,junc) + 1
                        stop = translation.find('*',junc)
                        tstop = stop if stop >= 0 else len(translation)
                    offset = (block_sum - i) % 3
                    trimmed = translation[tstart:tstop]
                    if debug:
                        print >> sys.stderr, "frame: %d\ttstart: %d  tstop: %d  offset: %d\t%s" % (i,tstart,tstop,offset,trimmed)
                    if filtering and tstart > ignore:
                        continue
                    #get genomic locations for start and end 
                    if self.strand == '+':
                        chromStart = self.chromStart + i + (tstart * 3)
                        chromEnd = self.chromEnd - offset - (len(translation) - tstop) * 3
                    else:
                        chromStart = self.chromStart + offset + (len(translation) - tstop) * 3
                        chromEnd = self.chromEnd - i - (tstart * 3)
                    #get the blocks for this translation
                    (tblockCount,tblockSizes,tblockStarts) = self.get_blocks(chromStart,chromEnd)
                    translations[i] = (chromStart,chromEnd,trimmed,tblockCount,tblockSizes,tblockStarts)
                    if debug:
                        print >> sys.stderr, "tblockCount: %d  tblockStarts: %s  tblockSizes: %s" % (tblockCount,tblockStarts,tblockSizes)
                    # translations[i] = (chromStart,chromEnd,trimmed,tblockCount,tblockSizes,tblockStarts)
        return translations


    def get_seq_id(self,seqtype='unk:unk',reference='',frame=None):
        ## Ensembl fasta ID format
        # >ID SEQTYPE:STATUS LOCATION GENE TRANSCRIPT
        # >ENSP00000328693 pep:splice chromosome:NCBI35:1:904515:910768:1 gene:ENSG00000158815:transcript:ENST00000328693 gene_biotype:protein_coding transcript_biotype:protein_coding
        frame_name = ''
        chromStart = self.chromStart
        chromEnd = self.chromEnd
        strand = 1 if self.strand == '+' else -1
        if frame != None:
            block_sum = sum(self.blockSizes)
            offset = (block_sum - frame) % 3
            frame_name = '_' + str(frame + 1)
            if self.strand == '+':
                chromStart += frame
                chromEnd -= offset
            else:
                chromStart += offset
                chromEnd -= frame
        location = "chromosome:%s:%s:%s:%s:%s" % (reference,self.chrom,chromStart,chromEnd,strand)
        seq_id = "%s%s %s %s" % (self.name,frame_name,seqtype,location)
        return seq_id


    def get_line(self, start_offset = 0, end_offset = 0):
        if start_offset or end_offset:
            s_offset = start_offset if start_offset else 0
            e_offset = end_offset if end_offset else 0
            if s_offset > self.chromStart:
                s_offset = self.chromStart
            chrStart = self.chromStart - s_offset
            chrEnd = self.chromEnd + e_offset
            blkSizes = self.blockSizes
            blkSizes[0] += s_offset
            blkSizes[-1] += e_offset
            blkStarts = self.blockStarts
            for i in range(1,self.blockCount):
                blkStarts[i] += s_offset
            items = [str(x) for x in [self.chrom,chrStart,chrEnd,self.name,self.score,self.strand,self.thickStart,self.thickEnd,self.itemRgb,self.blockCount,','.join([str(x) for x in blkSizes]),','.join([str(x) for x in blkStarts])]]
            return '\t'.join(items) + '\n'
        return self.line
